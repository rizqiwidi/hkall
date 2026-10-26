#!/bin/sh
# hkall installer — run once
set -e
pkg install -y python git termux-api 2>/dev/null || pkg install -y python git
if [ ! -d "$HOME/hkall" ]; then
  git clone https://github.com/rizqiwidi/hkall.git "$HOME/hkall"
else
  cd "$HOME/hkall" && git pull
fi
cd "$HOME/hkall"
chmod +x hkall.py
echo "hkall v0.3.2 installed"
echo "  TUI  -> python $HOME/hkall/hkall.py"
echo "  CLI  -> python $HOME/hkall/hkall.py --list"