"""Functionality for auto-generating markdown documentation.

Simply run `python generate_docs.py` from inside the `docs/` folder.
"""
import inspect
import os
import re
import toolz
import prefect


OUTLINE = [
    {
        "page": "environments.md",
        "classes": [
            prefect.environments.Secret,
            prefect.environments.Environment,
            prefect.environments.ContainerEnvironment,
            prefect.environments.PickleEnvironment,
        ],
        "title": "Environments",
    },
    {
        "page": "triggers.md",
        "functions": [
            prefect.triggers.all_finished,
            prefect.triggers.manual_only,
            prefect.triggers.always_run,
            prefect.triggers.never_run,
            prefect.triggers.all_successful,
            prefect.triggers.all_failed,
            prefect.triggers.any_successful,
            prefect.triggers.any_failed,
        ],
        "title": "Triggers",
    },
    {
        "page": "client.md",
        "classes": [
            prefect.client.Client,
            prefect.client.ClientModule,
            prefect.client.Projects,
            prefect.client.Flows,
            prefect.client.FlowRuns,
            prefect.client.TaskRuns,
        ],
        "title": "Client",
    },
    {
        "page": "schedules.md",
        "classes": [
            prefect.schedules.Schedule,
            prefect.schedules.NoSchedule,
            prefect.schedules.IntervalSchedule,
            prefect.schedules.CronSchedule,
            prefect.schedules.DateSchedule,
        ],
        "title": "Schedules",
    },
    {
        "page": "serializers.md",
        "classes": [prefect.serializers.Serializer, prefect.serializers.JSONSerializer],
        "title": "Serializers",
    },
    {"page": "core/edge.md", "classes": [prefect.core.edge.Edge], "title": "Edge"},
    {
        "page": "core/flow.md",
        "classes": [
            prefect.core.flow.Flow,
        ],
        "functions": [
            prefect.core.flow.get_hash,
            prefect.core.flow.xor,
        ],
        "title": "Flow",
    },
    {
        "page": "core/task.md",
        "classes": [prefect.core.task.Task, prefect.core.task.Parameter],
        "title": "Task",
    },
    {
        "page": "engine/cache_validators.md",
        "functions": [
            prefect.engine.cache_validators.never_use,
            prefect.engine.cache_validators.duration_only,
            prefect.engine.cache_validators.all_inputs,
            prefect.engine.cache_validators.all_parameters,
            prefect.engine.cache_validators.partial_parameters_only,
            prefect.engine.cache_validators.partial_inputs_only,
        ],
        "title": "Cache Validators",
    },
    {
        "page": "engine/state.md",
        "classes": [
            prefect.engine.state.State,
            prefect.engine.state.Pending,
            prefect.engine.state.CachedState,
            prefect.engine.state.Scheduled,
            prefect.engine.state.Retrying,
            prefect.engine.state.Running,
            prefect.engine.state.Finished,
            prefect.engine.state.Success,
            prefect.engine.state.Failed,
            prefect.engine.state.TriggerFailed,
            prefect.engine.state.Skipped,
        ],
        "title": "State",
    },
    {
        "page": "engine/signals.md",
        "classes": [
            prefect.engine.signals.PrefectStateSignal,
            prefect.engine.signals.FAIL,
            prefect.engine.signals.TRIGGERFAIL,
            prefect.engine.signals.SUCCESS,
            prefect.engine.signals.RETRY,
            prefect.engine.signals.SKIP,
            prefect.engine.signals.DONTRUN,
        ],
        "title": "Signals",
    },
    {
        "page": "engine/flow_runner.md",
        "classes": [prefect.engine.flow_runner.FlowRunner],
        "title": "FlowRunner",
    },
    {
        "page": "engine/task_runner.md",
        "classes": [prefect.engine.task_runner.TaskRunner],
        "title": "TaskRunner",
    },
    {
        "page": "engine/executors/dask.md",
        "classes": [prefect.engine.executors.dask.DaskExecutor],
        "title": "Dask Executor",
    },
    {
        "page": "engine/executors/base.md",
        "classes": [prefect.engine.executors.base.Executor],
        "title": "Executor",
    },
    {
        "page": "engine/executors/local.md",
        "classes": [prefect.engine.executors.local.LocalExecutor],
        "title": "Local Executor",
    },
    {
        "page": "utilities/collections.md",
        "classes": [
            prefect.utilities.collections.DotDict,
        ],
        "functions": [
            prefect.utilities.collections.merge_dicts,
            prefect.utilities.collections.to_dotdict,
            prefect.utilities.collections.dict_to_flatdict,
            prefect.utilities.collections.flatdict_to_dict,
        ],
        "title": "Collections",
    },
    {
        "page": "utilities/flows.md",
        "functions": [
            prefect.utilities.flows.reset_default_flow,
            prefect.utilities.flows.get_default_flow,
            prefect.utilities.flows.get_flow_by_id,
        ],
        "title": "Flow Utilities",
    },
    {
        "page": "utilities/tasks.md",
        "functions": [
            prefect.utilities.tasks.group,
            prefect.utilities.tasks.tags,
            prefect.utilities.tasks.as_task,
            prefect.utilities.tasks.task,
        ],
        "title": "Task Utilities",
    },
]


def preprocess(f):
    def wrapped(*args, **kwargs):
        new_obj = getattr(args[0], "__wrapped__", getattr(args[0], "func", args[0]))
        new_args = list(args)
        new_args[0] = new_obj
        return f(*new_args, **kwargs)

    return wrapped


def clean_line(line):
    line = (
        line.replace("Args:", "**Args**:")
        .replace("Returns:", "**Returns**:")
        .replace("Raises:", "**Raises**:")
    )
    return line.lstrip()


def format_lists(doc):
    "Convenience function for converting markdown lists to HTML for within-table lists"
    lists = re.findall(
        r"(Args\:)(.*?)\s+(-.*?)(\n\n|$)", doc, re.DOTALL
    )  # find formatted lists
    for section, _, items, _ in lists:
        list_items = re.split(r"-\s`", items)  # collect all list items
        block = ""
        for item in list_items:
            if item:
                block += "<li>`" + item + "</li>"
        list_block = f"<ul>{block}</ul>"
        doc = doc.replace(items + "\n\n", list_block).replace(items, list_block)
    return doc


def format_doc(doc, in_table=False):
    body = doc or ""
    code_blocks = re.findall(r"```(.*?)```", body, re.DOTALL)
    for num, block in enumerate(code_blocks):
        body = body.replace(block, f"$CODEBLOCK{num}")
    if in_table:
        body = format_lists(body)
    lines = body.split("\n")
    cleaned = "\n".join([clean_line(line) for line in lines])
    if in_table:
        cleaned = cleaned.replace("\n", "<br>").replace("```", "")
    for num, block in enumerate(code_blocks):
        if in_table:
            block = (
                '<pre class="language-python"><code class="language-python">'
                + block.rstrip("  ").replace("\n", "<br>")
                + "</code></pre>"
            )
        cleaned = cleaned.replace(f"$CODEBLOCK{num}", block.rstrip(" "))
    if in_table:
        return f"<sub>{cleaned}</sub><br>"
    else:
        return cleaned


def create_methods_table(members, title):
    table = ""
    if members:
        table = f"|{title} " + "&nbsp;" * 150 + "|\n"
        table += "|:----|\n"
    for method in members:
        table += format_subheader(method, level=2, in_table=True).replace(
            "\n", "<br><br>"
        )
        table += format_doc(inspect.getdoc(method), in_table=True)
        table += "|\n"
    return table


@preprocess
def get_call_signature(obj):
    assert callable(obj), f"{obj} is not callable, cannot format signature."
    # collect data
    sig = inspect.getfullargspec(obj)
    args, defaults = sig.args, sig.defaults or []
    varargs, varkwargs = sig.varargs, sig.varkw

    if args == []:
        standalone, kwargs = [], dict()
    else:
        if args[0] == "self":
            args = args[1:]  # remove self from displayed signature

        standalone = args[: -len(defaults)] if defaults else args  # true args
        kwargs = list(zip(args[-len(defaults) :], defaults))  # true kwargs

    varargs = [f"*{varargs}"] if varargs else []
    varkwargs = [f"*{varkwargs}"] if varkwargs else []

    return standalone, varargs, kwargs, varkwargs


@preprocess
def format_signature(obj):
    standalone, varargs, kwargs, varkwargs = get_call_signature(obj)
    # NOTE: I assume the call signature is f(x, y, ..., *args, z=1, ...,
    # **kwargs) and NOT f(*args, x, y, ...)
    psig = ", ".join(
        standalone + varargs + [f"{name}={val}" for name, val in kwargs] + varkwargs
    )
    return psig


@preprocess
def create_absolute_path(obj):
    dir_struct = inspect.getfile(obj).split("/")
    begins_at = dir_struct.index("src") + 1
    return ".".join([d.rstrip(".py") for d in dir_struct[begins_at:]])


@preprocess
def get_source(obj):
    base_url = "https://github.com/PrefectHQ/prefect/tree/master/src/prefect/"
    dir_struct = inspect.getfile(obj).split("/")
    begins_at = dir_struct.index("src") + 2
    line_no = inspect.getsourcelines(obj)[1]
    url_ending = "/".join(dir_struct[begins_at:]) + f"#L{line_no}"
    source_tag = f'<span style="float:right;">[[Source]]({base_url}{url_ending})</span>'
    return source_tag


@preprocess
def format_subheader(obj, level=1, in_table=False):
    class_sig = format_signature(obj)
    if level == 1 and inspect.isclass(obj):
        header = f"## {obj.__name__}\n\n###"
    elif not in_table:
        header = "##" + "#" * level
    else:
        header = "|"
    is_class = (
        '<span style="background-color:rgba(27,31,35,0.05);font-size:0.85em;">class</span>'
        if inspect.isclass(obj)
        else ""
    )
    class_name = f"{create_absolute_path(obj)}.{obj.__qualname__}"
    call_sig = (
        f" {header} {is_class} ```{class_name}({class_sig})```{get_source(obj)}\n"
    )
    return call_sig


if __name__ == "__main__":
    assert (
        os.path.basename(os.getcwd()) == "docs"
    ), "Only run this script from inside the docs/ directory!"

    for page in OUTLINE:
        # collect what to document
        fname, classes, fns = page["page"], page.get("classes", []), page.get("functions", [])
        fname = f"api/{fname}"
        directory = os.path.dirname(fname)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(fname, "w") as f:
            # PAGE TITLE / SETUP
            f.write("---\nsidebarDepth: 1\n---\n\n")
            title = page.get("title")
            if title:  # this would be a good place to have assignments
                f.write(f"# {title}\n---\n")

            for obj in classes:
                f.write(format_subheader(obj))

                f.write(format_doc(inspect.getdoc(obj)) + "\n\n")
                if type(obj) == toolz.functoolz.curry:
                    f.write("\n")
                    continue

                members = inspect.getmembers(
                    obj, predicate=lambda x: inspect.isroutine(x) and obj.__name__ in x.__qualname__
                )
                public_members = [method for (name, method) in members if not name.startswith("_")]
                f.write(create_methods_table(public_members, title="methods:"))
                f.write("\n")

            if fns:
                f.write("## Functions\n")
            f.write(create_methods_table(fns, title="functions:"))
            f.write("\n")
