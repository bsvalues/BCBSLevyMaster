{pkgs}: {
  deps = [
    pkgs.libiconv
    pkgs.jq
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
