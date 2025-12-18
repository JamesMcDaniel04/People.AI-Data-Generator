#!/usr/bin/env python3
"""Verify that the demo-gen package is properly installed and configured"""

import sys
from pathlib import Path


def check_python_version():
    """Check Python version is 3.9+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_package_installed():
    """Check if demo_gen package can be imported"""
    try:
        import demo_gen
        print(f"✅ demo_gen package installed (version {demo_gen.__version__})")
        return True
    except ImportError as e:
        print(f"❌ demo_gen package not found: {e}")
        print("   Run: pip install -e .")
        return False


def check_dependencies():
    """Check if all dependencies are installed"""
    dependencies = [
        "click",
        "yaml",
        "pydantic",
        "simple_salesforce",
        "openai",
        "dotenv",
        "rich",
    ]

    all_ok = True
    for dep in dependencies:
        module_name = dep.replace("-", "_")
        if module_name == "yaml":
            module_name = "yaml"
        elif module_name == "dotenv":
            module_name = "dotenv"

        try:
            __import__(module_name)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} not installed")
            all_ok = False

    return all_ok


def check_config_files():
    """Check if configuration files exist"""
    files_to_check = [
        ("demo.yaml", False, "Copy from demo.example.yaml"),
        ("demo.example.yaml", True, None),
        (".env", False, "Copy from .env.example and edit"),
        (".env.example", True, None),
    ]

    all_ok = True
    for filename, required, suggestion in files_to_check:
        path = Path(filename)
        if path.exists():
            print(f"✅ {filename}")
        elif required:
            print(f"❌ {filename} missing (required)")
            all_ok = False
        else:
            print(f"⚠️  {filename} missing (optional)")
            if suggestion:
                print(f"   {suggestion}")

    return all_ok


def check_cli_command():
    """Check if demo-gen CLI is available"""
    import subprocess

    try:
        result = subprocess.run(
            ["demo-gen", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            print(f"✅ demo-gen CLI available")
            return True
        else:
            print(f"❌ demo-gen command failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ demo-gen command not found in PATH")
        print("   Run: pip install -e .")
        return False
    except Exception as e:
        print(f"❌ Error checking CLI: {e}")
        return False


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Demo-Gen Installation Verification")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Package Installation", check_package_installed),
        ("Dependencies", check_dependencies),
        ("Configuration Files", check_config_files),
        ("CLI Command", check_cli_command),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 40)
        results.append(check_func())

    print("\n" + "=" * 60)
    if all(results):
        print("✅ All checks passed! Installation verified.")
        print("\nNext steps:")
        print("1. Edit .env with your Salesforce credentials")
        print("2. Edit demo.yaml with your configuration")
        print("3. Run: demo-gen dry-run -c demo.yaml")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
