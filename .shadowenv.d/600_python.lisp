(provide "python" "3.8.2")
(env/set "VIRTUAL_ENV" (expand-path "./.venv"))
(env/prepend-to-pathlist "PATH" (path-concat (env/get "VIRTUAL_ENV") "bin"))
