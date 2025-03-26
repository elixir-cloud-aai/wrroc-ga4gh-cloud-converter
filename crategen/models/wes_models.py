"""Each model in this module conforms to the corresponding WES model names as specified by the GA4GH schema (https://ga4gh.github.io/workflow-execution-service-schemas/docs/)."""

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator
from rfc3339_validator import validate_rfc3339  # type: ignore


class State(str, Enum):
    """Enumeration of workflow states.

    Attributes:
        UNKNOWN: The state of the workflow is unknown. This provides a safe default for messages where this field is missing.
        QUEUED: The workflow is queued.
        INITIALIZING: The workflow is initializing.
        RUNNING: The workflow is running.
        PAUSED: The workflow is paused.
        COMPLETE: The workflow has completed successfully.
        EXECUTOR_ERROR: The workflow encountered an executor error.
        SYSTEM_ERROR: The workflow encountered a system error.
        CANCELED: The workflow was canceled by the user.
        CANCELING: The workflow was canceled by the user, and is in the process of stopping.
        PREEMPTED: The workflow is stopped (preempted) by the system.
    """
    UNKNOWN = "UNKNOWN"
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CANCELED = "CANCELED"
    CANCELING = "CANCELING"
    PREEMPTED = "PREEMPTED"


class Log(BaseModel):
    """Log information for a workflow run or task.

    Attributes:
        name (`Optional[str]`): Task or workflow name
        cmd (`Optional[List[str]]`): Command line executed
        start_time (`Optional[str]`): When the task started executing (RFC 3339)
        end_time (`Optional[str]`): When the task ended (RFC 3339)
        stdout (`Optional[str]`): URL to retrieve standard output logs
        stderr (`Optional[str]`): URL to retrieve standard error logs
        exit_code (`Optional[int]`): Exit code of the program
        system_logs (`Optional[List[str]]`): Any logs the system decides are relevant
    """

    name: Optional[str] = None
    cmd: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    system_logs: Optional[List[str]] = None

    @validator("start_time", "end_time", allow_reuse=True)
    def validate_datetime(cls, value, field):
        """Check correct datetime format is RFC 3339"""
        if value and not validate_rfc3339(value):
            raise ValueError(
                f"The '{field.name}' property must be in RFC 3339 format"
            )
        return value


class TaskLog(Log):
    """Task execution log information.

    Attributes:
        id (`str`): Unique identifier which may be used to reference the task
        tes_uri (`Optional[str]`): Optional URL pointing to an extended task definition defined by a TES API
        name (`str`): REQUIRED The name of the task
    """

    id: str
    tes_uri: Optional[str] = None
    name: str = Field(...)


class RunRequest(BaseModel):
    """A workflow run request.

    Attributes:
        workflow_params (`dict[str, str]`): REQUIRED The workflow run parameterizations (JSON encoded)
        workflow_type (`str`): REQUIRED The workflow descriptor type (e.g., "CWL" or "WDL")
        workflow_type_version (`str`): REQUIRED The workflow descriptor type version
        tags (`Optional[dict[str, str]]`): Arbitrary key/value tags for the workflow
        workflow_engine_parameters (`Optional[dict[str, str]]`): Workflow engine specific parameters
        workflow_engine (`Optional[str]`): The workflow engine that should run this workflow
        workflow_engine_version (`Optional[str]`): The version of the workflow engine
        workflow_url (`str`): The workflow CWL or WDL document
    """

    workflow_params: dict[str, str]
    workflow_type: str
    workflow_type_version: str
    tags: Optional[dict[str, str]] = {}
    workflow_engine_parameters: Optional[dict[str, str]] = None
    workflow_engine: Optional[str] = None
    workflow_engine_version: Optional[str] = None
    workflow_url: str

    @root_validator()
    def validate_workflow_engine(cls, values):
        """Validate workflow engine dependencies."""
        engine_version = values.get("workflow_engine_version")
        engine = values.get("workflow_engine")
        if engine_version is not None and engine is None:
            raise ValueError(
                "The 'workflow_engine' attribute is required when the 'workflow_engine_version' attribute is set"
            )
        return values


class Run(BaseModel):
    """A workflow run.

    Attributes:
        run_id (`str`): Workflow run ID
        request (`Optional[RunRequest]`): The original workflow run request
        state (`Optional[State]`): Current state of the workflow run
        run_log (`Optional[Log]`): Log information about the workflow run
        task_logs_url (`Optional[str]`): URL for obtaining task logs
        task_logs (`Optional[List[Union[Log, TaskLog]]]`): DEPRECATED Task logs, use task_logs_url instead
        outputs (`dict[str, str]`): Output files produced by the workflow run
    """

    run_id: str
    request: Optional[RunRequest] = None
    state: Optional[State] = None
    run_log: Optional[Log] = None
    task_logs_url: Optional[str] = None
    task_logs: Optional[List[Union[Log, TaskLog]]] = None
    outputs: dict[str, str] = {}

    @root_validator
    def check_deprecated_fields(cls, values):
        """Check for usage of deprecated fields."""
        if values.get("task_logs") is not None:
            print(
                "DeprecationWarning: The 'task_logs' field is deprecated and will be removed in future versions. Use 'task_logs_url' instead."
            )
        return values
