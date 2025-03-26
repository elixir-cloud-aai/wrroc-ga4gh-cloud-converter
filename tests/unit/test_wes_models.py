"""Tests for WES models"""
import io
import sys

import pytest

from crategen.models.wes_models import (
    Log,
    Run,
    RunRequest,
    State,
    TaskLog,
)

# Test data constants
valid_datetime_strings = [
    "2020-10-02T16:00:00.000Z",
    "2024-10-15T18:14:34+00:00",
    "2024-10-15T18:14:34.948996+00:00",
    "2024-10-15T19:01:06.872464+00:00",
]

invalid_datetime_strings = [
    "2020-10-02 16:00:00",  # Missing 'T' separator
    "2020-10-02T16:00:00",  # Missing timezone
    "20201002T160000Z",  # Missing separators
    "2020-10-02T16:00:00.000+0200",  # Invalid timezone format
    "2020-10-02T16:00:00.000 GMT",  # Invalid timezone format
    "02-10-2020T16:00:00.000Z",  # Incorrect date order
]

test_url = "https://raw.githubusercontent.com/elixir-cloud-aai/CrateGen/refs/heads/main/README.md"

# Test data samples
test_workflow_params = {
    "reads": f"{test_url}/reads.fastq",
    "reference": f"{test_url}/reference.fa",
    "output_dir": f"{test_url}/results/"
}

test_workflow_engine_params = {
    "memory": "16GB",
    "cpu": "4",
    "disk_size": "100GB"
}

test_tags = {
    "project": "genomics-pipeline",
    "sample": "TCGA-AB-2823",
    "analysis": "variant-calling"
}


class TestState:
    """Test suite for State enum"""

    def test_state_enum_values(self):
        """Test that State enum has correct values from GA4GH spec"""
        assert State.UNKNOWN == "UNKNOWN"
        assert State.QUEUED == "QUEUED"
        assert State.INITIALIZING == "INITIALIZING"
        assert State.RUNNING == "RUNNING"
        assert State.PAUSED == "PAUSED"
        assert State.COMPLETE == "COMPLETE"
        assert State.EXECUTOR_ERROR == "EXECUTOR_ERROR"
        assert State.SYSTEM_ERROR == "SYSTEM_ERROR"
        assert State.CANCELED == "CANCELED"
        assert State.CANCELING == "CANCELING"
        assert State.PREEMPTED == "PREEMPTED"


class TestLog:
    """Test suite for Log model"""

    def test_log_datetime_validation(self):
        """Test datetime validation in Log"""
        for valid_datetime in valid_datetime_strings:
            log = Log(
                name="workflow_123",
                start_time=valid_datetime,
                end_time=valid_datetime
            )
            assert log.start_time == valid_datetime
            assert log.end_time == valid_datetime

        for invalid_datetime in invalid_datetime_strings:
            with pytest.raises(ValueError) as exc_info:
                Log(
                    name="workflow_123",
                    start_time=invalid_datetime
                )
            assert "format" in str(exc_info.value)


class TestTaskLog:
    """Test suite for TaskLog model"""

    def test_task_log_required_fields(self):
        """Test that required fields must be provided"""
        with pytest.raises(ValueError):
            TaskLog(id="task-123")  # Missing required name field

        # Test with required fields
        task_log = TaskLog(
            id="task-123",
            name="alignment"
        )
        assert task_log.id == "task-123"
        assert task_log.name == "alignment"

    def test_task_log_all_fields(self):
        """Test TaskLog with all fields"""
        task_log = TaskLog(
            id="task-bwa-mem-123",
            name="bwa_mem_alignment",
            cmd=["bwa", "mem", "-t", "4", "reference.fa", "reads.fastq"],
            stdout="https://storage.googleapis.com/workflow-logs/task123/stdout.log",
            stderr="https://storage.googleapis.com/workflow-logs/task123/stderr.log",
            exit_code=0,
            tes_uri=test_url
        )
        assert task_log.id.startswith("task-")
        assert task_log.name == "bwa_mem_alignment"
        assert task_log.stdout.startswith("https://")
        assert task_log.stderr.startswith("https://")
        assert task_log.tes_uri == test_url


class TestRunRequest:
    """Test suite for RunRequest model"""

    def test_run_request_required_fields(self):
        """Test that required fields must be provided"""
        with pytest.raises(ValueError):
            RunRequest(workflow_type="CWL")  # Missing other required fields

        request = RunRequest(
            workflow_params={"input": "test.txt"},
            workflow_type="CWL",
            workflow_type_version="v1.0",
            workflow_url=test_url
        )
        assert request.workflow_type == "CWL"
        assert request.workflow_url == test_url

    def test_workflow_engine_validation(self):
        """Test workflow engine validation rules"""
        # Version without engine should fail
        with pytest.raises(ValueError) as exc_info:
            RunRequest(
                workflow_params={},
                workflow_type="CWL",
                workflow_type_version="v1.0",
                workflow_url=test_url,
                workflow_engine_version="3.1.0"
            )
        assert "workflow_engine" in str(exc_info.value)

        # Both engine and version should work
        request = RunRequest(
            workflow_params={},
            workflow_type="CWL",
            workflow_type_version="v1.0",
            workflow_url=test_url,
            workflow_engine="cwltool",
            workflow_engine_version="3.1.0"
        )
        assert request.workflow_engine == "cwltool"
        assert request.workflow_engine_version == "3.1.0"


class TestRun:
    """Test suite for Run model"""

    def test_run_required_fields(self):
        """Test that required fields must be provided"""
        run = Run(run_id="run-123")
        assert run.run_id == "run-123"
        assert run.outputs == {}

    def test_task_logs_deprecation(self):
        """Test deprecation warning for task_logs field"""
        task_log = TaskLog(
            id="task-123",
            name="alignment"
        )
        
        # Capture stdout to test deprecation warning
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        Run(
            run_id="run-123",
            task_logs=[task_log]
        )
        
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "DeprecationWarning" in output
        assert "task_logs" in output
        assert "task_logs_url" in output

    def test_run_output_urls(self):
        """Test Run accepts outputs with different URL schemes"""
        output_urls = {
            "http_url": "http://example.com/output.txt",
            "https_url": "https://storage.googleapis.com/output.txt",
            "s3_url": "s3://my-bucket/output.txt",
            "gs_url": "gs://my-bucket/output.txt",
            "file_url": "file:///local/path/output.txt",
            "absolute_path": "/absolute/path/output.txt",
            "relative_path": "./relative/path/output.txt"
        }
        
        run = Run(run_id="run-123", outputs=output_urls)
        
        # Verify all output URLs are preserved
        for key, value in output_urls.items():
            assert run.outputs[key] == value
