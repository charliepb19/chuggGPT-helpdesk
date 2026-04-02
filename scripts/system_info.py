import platform
import socket

def main():
    lines = [
        f"System: {platform.system()}",
        f"Node Name: {platform.node()}",
        f"Release: {platform.release()}",
        f"Version: {platform.version()}",
        f"Machine: {platform.machine()}",
        f"Processor: {platform.processor()}",
        f"Hostname: {socket.gethostname()}"
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    print(main())