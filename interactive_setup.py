import sys
import venv
import os
import subprocess
import questionary


def create_virtual_environment():
    venv_dir = os.path.join(os.getcwd(), 'venv')
    venv.create(venv_dir, with_pip=True)
    activate_script = os.path.join(venv_dir, 'bin', 'activate')
    return activate_script


def install_dependencies():
    subprocess.run([sys.executable, '-m', 'pip', 'install',
                   '-r', 'requirements.txt'], check=True)


def global_installation():
    subprocess.run([sys.executable, '-m', 'pip', 'install', '.'], check=True)


def docker_setup():
    subprocess.run(['docker', 'build', '-t',
                   'strava-to-trainingpeaks', '.'], check=True, shell=False)
    subprocess.run(['docker', 'run', '-it', '--rm',
                   'strava-to-trainingpeaks'], check=True, shell=False)


def main():
    setup_method = questionary.select(
        "Choose your preferred setup method:",
        choices=["Global installation", "Virtual environment", "Docker"]
    ).ask()

    if setup_method == "Global installation":
        global_installation()
    elif setup_method == "Virtual environment":
        activate_script = create_virtual_environment()
        install_dependencies()
        print(
            f"Virtual environment created. Activate it using 'source {activate_script}'")
    elif setup_method == "Docker":
        docker_setup()
    else:
        print("Invalid setup method selected.")


if __name__ == "__main__":
    main()
