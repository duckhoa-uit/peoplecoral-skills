#!/usr/bin/env bash
# Flavor → application id. Source this file; call bundle_id <flavor>.
# Default flavor is wpseoai (production). Unknown flavor exits 2.
bundle_id() {
  case "${1:-wpseoai}" in
    dev) echo com.peoplecoral.dev ;;
    demo) echo com.peoplecoral.demo ;;
    wpseoai) echo com.wpseoai.peoplecoral ;;
    *) echo "unknown flavor: $1 (dev|demo|wpseoai)" >&2; return 2 ;;
  esac
}
