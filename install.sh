#!/bin/sh
# hkall installer
set -e
pkg install -y python git
if [ ! -d "$HOME/hkall" ]; then
  git clone https://github.com/rizqiwidi/hkall.git "$HOME/hkall"
fi
cd "$HOME/hkall"
chmod +x hkall.py
echo "hkall installed → run: python $HOME/hkall/hkall.py"
