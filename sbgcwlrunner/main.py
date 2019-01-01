"""CWL E Coyote: A CWL Runner for the Seven Bridges Genomics cloud platform

Usage:
    sbg-cwl-runner [--outdir=<od>] [--quiet] [--api-profile=<prof>] [--project=<proj>] [--poll-interval=<poll>] WORKFLOW [JOB]

Options:
    -h --help               Show help screen
    --outdir=<od>           Directory to put results in [default: ./]
    --quiet                 Suppress logging messages
    --api-profile=<prof>    API profile name [default: default]
    --project=<proj>        Project to run tasks in [default: default-sbg-cwl-runner-project]
    --poll-interval=<poll>  Polling interval to check for job status (in min) [default: 1]
"""
import os
import sys
import time
import pathlib
import yaml
import json
import hashlib

from docopt import docopt
import sevenbridges as sbg
import sevenbridges.errors as sbgerr
from sevenbridges.http.error_handlers import (
    general_error_sleeper, maintenance_sleeper, rate_limit_sleeper
)
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)


def is_workflow(doc):
    """Is this document a workflow?

    :param doc:
    :return:
    """
    return doc["class"] == "Workflow"


def recursive_workflow_load(wf_fname):
    """Load wf_name and then, recursively, embed any steps that invoke other
     workflows

    :param wf_fname:
    :return:
    """
    doc = yaml.load(open(wf_fname, 'r'))
    if is_workflow(doc):
        for n in range(len(doc["steps"])):
            if isinstance(doc["steps"][n]["run"], str):
                step_cwl = doc["steps"][n]["run"]
                if not step_cwl.startswith("/"):
                    step_cwl = os.path.join(os.path.dirname(wf_fname), step_cwl)
                doc["steps"][n]["run"] = recursive_workflow_load(step_cwl)
    return doc


def get_project(api, uname, project):
    try:
        full_project_id = uname + "/" + project
        return api.projects.get(full_project_id).id
    except sbgerr.NotFound:
        logger.error("Project not found: {}".format(project))
        exit(1)


def get_app_hash(raw_cwl):
    """If the CWL has a field "sbg:hash" (as used by sevenbridges-cwl) use that,
    else compute it (again, just like sevenbridges-cwl)

    :param raw_cwl:
    :return:
    """
    if "sbg:hash" in raw_cwl:
        return raw_cwl["sbg:hash"]
    else:
        sha = hashlib.sha512()
        sha.update(json.dumps(raw_cwl, sort_keys=True).encode('utf-8'))
        return sha.hexdigest()


def upload_app(api, project, raw_cwl):
    """Given the raw cwl app (as a Python dict) upload it to the platform

    :param api:
    :param project:
    :param app:
    :return:
    """
    raw_cwl["sbg:hash"] = get_app_hash(raw_cwl)
    full_app_id = project + "/" + raw_cwl["id"]

    try:
        app = api.apps.get(full_app_id)
        if get_app_hash(raw_cwl) == get_app_hash(app.raw):
            logger.debug("Using existing app: {}".format(full_app_id))
            return app
        else:
            logger.debug("Creating revised app: {}".format(full_app_id))
            return api.apps.create_revision(
                id=full_app_id,
                raw=raw_cwl,
                revision=app.revision + 1
            )
    except sbgerr.NotFound:
        logger.debug("Creating new app: {}".format(full_app_id))
        return api.apps.install_app(
            id=full_app_id,
            raw=raw_cwl
        )


def load_job(job_fname):
    job = {}
    if job_fname:
        with open(job_fname, "r") as f:
            if job_fname.endswith(('json',)):
                job = json.load(f)
            elif job_fname.endswith(('yaml', 'yml')):
                job = yaml.load(f)
            else:
                raise RuntimeError("Job file must be json or YAML")
    return job


def fill_out_job_defaults(job, cwl_doc):
    for inp in cwl_doc["inputs"]:
        if inp["id"] not in job:
            if "default" in inp:
                job[inp["id"]] = inp["default"]
    return job


def resolve_job(api, full_project_id, job_node, base_path):
    """Resolve file ids for files indicated in the job dict.

    :param api:
    :param full_project_id:
    :param job_node:
    :param base_path:
    :return:
    """
    if isinstance(job_node, dict):
        if job_node.get("class", None) == "File":
            # The SBG platform uses "path"
            if "location" in job_node:
                key = "location"
            else:
                key = "path"
            job_node = resolve_file(api, full_project_id, job_node[key],
                                    base_path)
            return job_node
        else:
            return {
                k: resolve_job(api, full_project_id, v, base_path)
                for k, v in job_node.items()
                }
    elif isinstance(job_node, list):
        return [resolve_job(api, full_project_id, v, base_path) for v in
                job_node]
    else:
        return job_node


def resolve_file(api, full_project_id, file_path, base_path):
    """Upload the local file to the project if needed.

    :param api:
    :param full_project_id:
    :param file_path:
    :param base_path:
    :return:
    """
    # Handle pre-existing IDs in input JSON
    basename = pathlib.PurePath(file_path).name
    if not pathlib.Path(file_path).exists():
        return api.files.get(basename)
    fl = list(api.files.query(project=full_project_id, names=[basename]))
    if len(fl) == 1:
        return fl[0]
    else:
        if pathlib.PurePath(file_path).is_absolute():
            full_file_path = file_path
        else:
            full_file_path = str(
                pathlib.PurePath(pathlib.PurePath(base_path).parent, file_path))

        logger.debug("Uploading file: {}".format(full_file_path))
        if pathlib.Path(full_file_path).stat().st_size == 0:
            # SBG API has a bug where it can't upload 0 byte files
            logger.warn("Working around zero-size SBG API bug")
            open('onebytefile.txt', 'w').write(" ")
            F = api.files.upload(project=full_project_id,
                                 path="onebytefile.txt",
                                 file_name=basename).result()
            os.remove("onebytefile.txt")
            return F
        else:
            return api.files.upload(project=full_project_id,
                                    path=full_file_path).result()


def resolve_output_dict(output_node, outdir):
    """Given an output task json, download any produced files and return the
    output json with the filenames resolved

    :param output_node:
    :param outdir:
    :return:
    """
    if isinstance(output_node, dict):
        return {
            k: resolve_output_dict(v, outdir)
            for k, v in output_node.items()
            }
    elif isinstance(output_node, list):
        return [resolve_output_dict(v, outdir) for v in output_node]
    else:
        if isinstance(output_node, sbg.File):
            out_path = pathlib.PurePath(outdir, output_node.name)
            output_node.download(path=str(out_path))
            return {
                "class": "File",
                "path": output_node.name
            }
        else:
            return output_node


def main():
    arguments = docopt(__doc__, version='2018.11')

    if arguments['--quiet']:
        logger.setLevel(level=logging.ERROR)
    else:
        logger.setLevel(level=logging.DEBUG)

    config = sbg.Config(arguments["--api-profile"])
    api = sbg.Api(config=config, error_handlers=[
        rate_limit_sleeper,
        maintenance_sleeper,
        general_error_sleeper])
    cwl_doc = recursive_workflow_load(arguments["WORKFLOW"])
    if "id" not in cwl_doc:
        cwl_doc["id"] = pathlib.PurePath(arguments["WORKFLOW"]).stem

    uname = api.users.me().username

    full_project_id = get_project(api, uname, arguments["--project"])
    logger.debug("Using project: {}".format(full_project_id))

    app = upload_app(api, full_project_id, cwl_doc)
    logger.debug("Using app: {}".format(app.id))

    job = load_job(arguments["JOB"])
    job = fill_out_job_defaults(job, cwl_doc)
    task_name = "{}: {}".format(app.name,
                                hashlib.sha1(str(job).encode()).hexdigest()[
                                :10])

    job = resolve_job(api, full_project_id, job,
                      pathlib.PurePath(arguments["JOB"]))

    task = api.tasks.create(
        name=task_name,
        project=full_project_id,
        app=app,
        inputs=job,
        interruptible=False,
        run=True)

    while task.status not in ["ABORTED", "COMPLETED", "FAILED"]:
        task.reload()
        time.sleep(float(arguments["--poll-interval"]) * 60)

    # Output required in CWL Output Object Document format
    # which expects property name enclosed in double quotes
    print(json.dumps(resolve_output_dict(task.outputs, arguments["--outdir"]),
                     indent=4, separators=(',', ': ')))
