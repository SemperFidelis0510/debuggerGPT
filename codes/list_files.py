import os


def list_files(directory):
    for filename in os.listdir(directory):
        print(filename)


if __name__ == "__main__":
    list_files("P:/Scripts/debuggerGPT/codes")
