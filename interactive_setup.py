import os
import subprocess
import questionary

def create_virtualenv():
    subprocess.run(["python3", "-m", "venv", "env"])
    print("Virtual environment created successfully.")

def install_dependencies():
    subprocess.run(["env/bin/pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully.")

def global_install():
    subprocess.run(["pip", "install", "."])
    print("Package installed globally.")

def docker_setup():
    subprocess.run(["docker", "build", "-t", "strava-to-trainingpeaks", "."])
    subprocess.run(["docker", "run", "-it", "--rm", "strava-to-trainingpeaks"])
    print("Docker container setup and running.")

def main():
    setup_method = questionary.select(
        "Choose your preferred setup method:",
        choices=["Global installation", "Virtual environment", "Docker"]
    ).ask()

    if setup_method == "Global installation":
        global_install()
    elif setup_method == "Virtual environment":
        create_virtualenv()
        install_dependencies()
    elif setup_method == "Docker":
        docker_setup()
    else:
        print("Invalid setup method selected.")

if __name__ == "__main__":
    main()
