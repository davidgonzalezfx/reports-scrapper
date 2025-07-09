FROM mcr.microsoft.com/windows/servercore:ltsc2022

# Install Python
RUN powershell -Command \
    Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.9.7/python-3.9.7.exe -OutFile python-3.9.7.exe; \
    Start-Process -Wait -FilePath python-3.9.7.exe /quiet InstallAllUsers=1 PrependPath=1; \
    Remove-Item -Force python-3.9.7.exe

# Install PyInstaller
RUN pip install pyinstaller

# Copy the app files to the container
COPY . /app

# Set working directory
WORKDIR /app

# Build the executable for Windows
RUN pyinstaller --onefile app.py
