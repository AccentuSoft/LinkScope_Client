#!/bin/bash

# Spec for .desktop files:
# https://specifications.freedesktop.org/menu-spec/latest/apcs02.html
# https://specifications.freedesktop.org/menu-spec/latest/index.html

read -r -d '' HELPTEXT << EOF
== Installation script for LinkScope Client for Ubuntu 20.04 or greater ==

Usage:
------
bash $0 install
- or -
bash $0 uninstall

Instructions:
-------------
Run the script as a user with sudo permissions, with either 'install' or 'uninstall' (no quotes) as the one and only parameter.
The script will then install or uninstall the software for all users on the computer.

Function:
---------
The script will update the package repositories, and attempt to install the following packages:
p7zip-full curl libopengl0 graphviz libmagic1

Then, the script will download the latest version of the software from AccentuSoft's repository, add it to /usr/local/sbin, and optionally create a Desktop shortcut for the software.
EOF

read -r -d '' DESKTOP_ENTRY << EOF
[Desktop Entry]
Name=LinkScope Client
StartupWMClass=LinkScope Client
Comment=Start LinkScope Client
GenericName=Investigation Software
Terminal=false
Exec=/usr/local/sbin/LinkScope/LinkScope
Icon=/usr/local/sbin/LinkScope/Icon.ico
Type=Application
Categories=Application;Office;DataVisualization;
MimeType=application/linkscope
Keywords=LinkScope;Investigation;Graph;Knowledge
EOF


# Make sure we're not running as root.
if [ "$EUID" -eq 0 ]; then
  echo "Please run the installation script as a user with sudo permissions, not as root."
  exit
fi

if [ "$#" -ne 1 ]; then
  echo "$HELPTEXT"
  exit
fi

echo "Sudo permission check"
sudo echo "Sudo permissions available"

if [ "$?" -ne 0 ]; then
  echo "Sudo permissions not available, aborting."
  exit
fi

if [ "$1" == "install" ]; then
  echo "Installing Software"
  echo "Updating Packages"
  sudo apt update
  echo "Installing New Packages"
  sudo apt install p7zip-full curl libopengl0 graphviz libmagic1 -y
  echo "Downloading latest version of LinkScope client..."
  linuxURL=$(curl -sL https://github.com/AccentuSoft/LinkScope_Client/releases/latest | grep 'Ubuntu-x64.7z' -m 1 | cut -d '"' -f 2 | tr -d ' ')
  curl -L https://github.com${linuxURL} -o /tmp/LinkScope.7z
  sudo 7z x /tmp/LinkScope.7z -o/usr/local/sbin/ && rm /tmp/LinkScope.7z
  if [ $? -ne 0 ]; then
    echo "Something went wrong during the download or extraction."
    echo "Please check that /tmp/LinkScope.7z exists, and that it is an archive containing the latest version of the LinkScope Client software."
    exit
  fi
  sudo echo "$DESKTOP_ENTRY" > /tmp/LinkScope.desktop
  sudo mv /tmp/LinkScope.desktop /usr/share/applications/LinkScope.desktop
  sudo chmod +x /usr/share/applications/LinkScope.desktop
  read -p "Create a Desktop shortcut? WARNING: This will refresh the desktop! [y/N]" -n 1 -r
  # https://askubuntu.com/a/1014261    -- Making Desktop launchers with .desktop files
  # https://stackoverflow.com/a/62240478   -- Making .desktop files work.
  # Not refreshing the desktop would mean that the desktop icon starts working after a restart.
  # Manually creating a desktop icon through the gui is simpler; after creating a symlink, the user can right-click
  #   the .desktop file and select 'Allow Launching'. This however requires user interaction.
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    ln -s /usr/share/applications/LinkScope.desktop ${HOME}/Desktop/LinkScope.desktop
    dbus-launch gio set ${HOME}/Desktop/LinkScope.desktop "metadata::trusted" true
    dbus-send --type=method_call --print-reply --dest=org.gnome.Shell /org/gnome/Shell org.gnome.Shell.Eval string:'global.reexec_self()'
  fi
  echo "Done."
  exit
fi

if [ "$1" == "uninstall" ]; then
  echo "Removing Software"
  sudo rm -rf /usr/local/sbin/LinkScope
  sudo rm /usr/share/applications/LinkScope.desktop
  rm ${HOME}/Desktop/LinkScope.desktop

  echo "Done."
  echo "Note that the system packages used by the software are not removed, in the case that they are necessary for other software to function."
  exit
fi

# If the argument passed in is not 'install' or 'uninstall', print the help message.
echo "$HELPTEXT"
