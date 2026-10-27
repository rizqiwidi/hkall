# hkall bash completion — source this in ~/.bashrc:
#   [ -f $HOME/hkall/bin/hkall-completion.bash ] && source $HOME/hkall/bin/hkall-completion.bash
_hkall() {
  local cur prev words cword
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  # module keys: parse from `hkall --list`
  local keys
  keys="$(HKALL_NOPLUGIN=1 hkall --list 2>/dev/null | awk '{print $1}')"
  if [[ "$prev" == "-m" || "$prev" == "--module" ]]; then
    COMPREPLY=( $(compgen -W "$keys" -- "$cur") )
    return
  fi
  case "$cur" in
    -*) COMPREPLY=( $(compgen -W "--host --port --ports --out --list --search -m --module" -- "$cur") ); return ;;
  esac
}
complete -F _hkall hkall
