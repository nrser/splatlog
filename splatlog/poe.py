def tasks():
    return {
        "tasks": {
            "splatlog:report": {
                "script": "splatlog:report",
                "help": "Print a logging system report.",
                "args": [
                    {
                        "name": "include",
                        "help": "Include all loggers or just those that have been configured?",
                        "options": ["-i", "--include"],
                        "choices": ["all", "configured"],
                        "default": "all",
                    },
                    {
                        "name": "console",
                        "help": "Where to print, via a `rich.console.Console`.",
                        "options": ["-c", "--console"],
                        "choices": ["stdout", "stderr"],
                    },
                    {
                        "name": "show_placeholder_loggers",
                        "help": "Show `logging.PlaceHolder` entries.",
                        "type": "boolean",
                        "options": ["-p", "--placeholders"],
                        "default": False,
                    },
                    {
                        "name": "show_null_handlers",
                        "help": "Show `logging.NullHandler` entries.",
                        "type": "boolean",
                        "options": ["-n", "--nulls"],
                        "default": False,
                    },
                ],
            }
        }
    }
