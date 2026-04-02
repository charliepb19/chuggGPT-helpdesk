import platform
import subprocess

def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return result.stderr.strip()
        return result.stdout.strip()
    except Exception as e:
        return f"Error running command {' '.join(command)}: {e}"

def main():
    system = platform.system().lower()

    if system == "windows":
        ping_cmd = ["ping", "8.8.8.8"]
    else:
        ping_cmd = ["ping", "-c", "4", "8.8.8.8"]

    output = []
    output.append("=== Ping Test to 8.8.8.8 ===")
    output.append(run_command(ping_cmd))

    return "\n".join(output)

if __name__ == "__main__":
    print(main())