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
chmod +x hkall.py bin/hkall

# global `hkall` command: symlink into PATH (Termux prefix or /usr/local/bin)
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
BINDIR="$PREFIX/bin"
if [ -d "$BINDIR" ] && [ -w "$BINDIR" ]; then
  ln -sf "$HOME/hkall/bin/hkall" "$BINDIR/hkall"
  echo "hkall command installed -> $BINDIR/hkall"
else
  mkdir -p "$HOME/bin" 2>/dev/null && ln -sf "$HOME/hkall/bin/hkall" "$HOME/bin/hkall" \
    && echo "hkall command installed -> ~/bin/hkall (ensure ~/bin in PATH)" \
    || echo "could not install global command; use: python $HOME/hkall/hkall.py"
fi

# shell completion (bash/zsh)
case "$(basename "$SHELL")" in
  zsh)  ln -sf "$HOME/hkall/bin/hkall-completion.zsh" "$HOME/.oh-my-zsh/custom/hkall.zsh" 2>/dev/null \
          && echo "zsh completion linked (reuse ~/.oh-my-zsh/custom)" 2>/dev/null || true ;;
esac

echo "hkall $(grep -o 'VERSION = \"[^\"]*\"' hkall.py | cut -d'\"' -f2) installed"
echo "  TUI  -> hkall"
echo "  CLI  -> hkall --list"
echo "  help -> hkall -m scan --help"
