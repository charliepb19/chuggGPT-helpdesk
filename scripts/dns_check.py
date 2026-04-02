import socket

def main():
    try:
        ip = socket.gethostbyname("google.com")
        return f"DNS resolution successful: google.com -> {ip}"
    except Exception as e:
        return f"DNS resolution failed: {e}"

if __name__ == "__main__":
    print(main())