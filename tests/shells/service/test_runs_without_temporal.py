import subprocess
import sys
import textwrap


def test_the_core_of_the_service_loads_and_imports_nothing_from_temporal():
    code = textwrap.dedent(
        """
        import sys
        sys.modules["temporalio"] = None
        import veil.shells.service.run_repo
        import veil.shells.service.classify_failure
        import veil.shells.service.checkout_sweep
        import veil.shells.service.models.service_dependencies
        """
    )

    result = subprocess.run(
        [sys.executable, "-I", "-c", code], check=False, capture_output=True, text=True
    )

    assert result.returncode == 0, result.stderr
