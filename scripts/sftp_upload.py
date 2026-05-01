import os
import paramiko

local_file = os.path.join(os.path.dirname(__file__), "../data/input/top_directors_data.csv")
remote_path = "/upload/top_directors_data.csv"

transport = None
sftp = None
try:
    transport = paramiko.Transport(("localhost", 2222))
    transport.connect(username="sftp", password="password")

    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(local_file, remote_path)

    print("File uploaded successfully!")

except Exception as e:
    print(f"Upload failed: {e}")

finally:
    if sftp is not None:
        sftp.close()
    if transport is not None:
        transport.close()