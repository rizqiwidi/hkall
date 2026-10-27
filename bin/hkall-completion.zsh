# hkall zsh completion — source this in ~/.zshrc:
#   [ -f $HOME/hkall/bin/hkall-completion.zsh ] && source $HOME/hkall/bin/hkall-completion.zsh
_hkall() {
  local cur
  cur=${words[CURRENT]}
  local keys
  keys="$(HKALL_NOPLUGIN=1 hkall --list 2>/dev/null | awk '{print $1}')"
  if [[ ${words[CURRENT-1]} == "-m" || ${words[CURRENT-1]} == "--module" ]]; then
    compadd -- ${(f)keys}
    return
  fi
  if [[ "$cur" == -* ]]; then
    compadd -- '--host' '--port' '--ports' '--out' '--list' '--search' '-f' '--module'
  fi
}
compdef _hkall hkall
