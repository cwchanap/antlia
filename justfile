# Antila task runner. Run `just` (no args) to list recipes.

set positional-arguments

# List available recipes (default)
default:
    @just --list

# Build C#, import assets, launch. Extra args go to Godot, e.g. `just run --headless -- --self-test`
run *args:
    ./run.command "$@"
