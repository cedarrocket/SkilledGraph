"""Shared terminal input for chat and first-run setup."""
from contextlib import closing, contextmanager


@contextmanager
def terminal_reader(input_stream, error_stream):
    """Use a line editor for real terminals; allow injected text streams."""
    try:
        input_stream.fileno()
    except (AttributeError, OSError):
        def read(prompt, *, is_password=False):
            print(prompt, end="", file=error_stream, flush=True)
            line = input_stream.readline()
            if line == "":
                raise EOFError
            return line.rstrip("\r\n")
        yield read
        return
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import DummyHistory
    from prompt_toolkit.input import create_input
    from prompt_toolkit.output import create_output

    with closing(create_input(stdin=input_stream)) as terminal_input:
        session = PromptSession(input=terminal_input,
                                output=create_output(stdout=error_stream))
        secret_session = PromptSession(input=terminal_input,
                                       output=session.output, history=DummyHistory())
        def read(prompt, *, is_password=False):
            selected = secret_session if is_password else session
            return selected.prompt(prompt, is_password=is_password)
        yield read

