(provide "python" "3.12")
(env/set "VIRTUAL_ENV" (expand-path "./.venv"))
(env/prepend-to-pathlist "PATH" (path-concat (env/get "VIRTUAL_ENV") "bin"))
