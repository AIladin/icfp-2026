{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  packages = [ ];

  # One shared cargo target dir, so maturin's isolated build of `littleman-rs` (uv runs it in its
  # own environment) reuses the same incremental cache as a plain `cargo build`.
  env.CARGO_TARGET_DIR = "${config.devenv.root}/rs/target";

  # `lmr` is the Rust runner; `cargo build --release` puts it here. The Python `lm` stays on PATH
  # from the venv — the two take the same flags on purpose, so either name works.
  enterShell = ''
    export PATH="${config.devenv.root}/rs/target/release:$PATH"
  '';

  # Exports ICFP_API_KEY (and anything else in the gitignored repo-root .env) into the shell, so the
  # `icfp` CLI picks the key up from the environment no matter which directory it runs from.
  dotenv.enable = true;

  languages.rust = {
    enable = true;
    channel = "stable";

    components = [
      "rustc"
      "cargo"
      "clippy"
      "rustfmt"
      "rust-analyzer"
    ];
  };

  languages.python = {

    enable = true;
    venv.enable = true;
    directory = "./py";

    uv = {
      enable = true;
      sync.enable = true;
    };

  };
  # The cargo workspace is at `rs/`, but the hooks run from the repo root — where there is no
  # `Cargo.toml`, so the stock entries fail with "could not find Cargo.toml". Point them at the
  # manifest. `.pre-commit-config.yaml` is generated from this and must never be edited directly.
  git-hooks.hooks = {
    rustfmt = {
      enable = true;
      entry = lib.mkForce "cargo fmt --manifest-path rs/Cargo.toml --all -- --check";
      pass_filenames = false;
    };
    clippy = {
      enable = true;
      entry = lib.mkForce "cargo clippy --manifest-path rs/Cargo.toml --all-targets -- -D warnings";
      pass_filenames = false;
    };
    ruff.enable = true;
  };

  # See full reference at https://devenv.sh/reference/options/
}
