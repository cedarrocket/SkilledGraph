"""Useful tools, with the same argument/path validation at gate and execution."""
import json
from pathlib import PurePosixPath
from langchain_core.tools import tool
from skilledgraph.monty_execution import run_monty, bounded_json
from .filesystem_cn import Workspace
from .shell_cn import bash as run_bash


class Toolkit:
    def __init__(self, workspace):
        self.workspace = Workspace(workspace)
        @tool
        def read_file(path: str, start_line: int = 1, max_lines: int = 200) -> str:
            """Read UTF-8 workspace file with line numbers. Cannot read private paths or links."""
            if start_line < 1 or not 1 <= max_lines <= 400:
                raise ValueError('Invalid line bounds')
            lines=self.workspace.read(path).splitlines()
            selected=lines[start_line-1:start_line-1+max_lines]
            text='\n'.join(f'{i}: {line}' for i,line in enumerate(selected,start_line))
            return json.dumps({'path':path,'total_lines':len(lines),'text':text[:12000],
                'truncated':len(text)>12000 or start_line-1+max_lines<len(lines)},ensure_ascii=False)
        @tool
        def list_files(path: str = '.') -> str:
            """List up to 500 direct workspace children, excluding private paths and links."""
            return json.dumps(self.workspace.entries(path),ensure_ascii=False)
        @tool
        def search_files(query: str, path: str = '.') -> str:
            """Literal substring search in UTF-8 workspace files; bounded traversal, no regex."""
            if not query or len(query)>500: raise ValueError('Query must contain 1..500 characters')
            pending=[path]; visited=0; matches=[]
            while pending and visited<500 and len(matches)<50:
                directory=pending.pop()
                for entry in self.workspace.entries(directory):
                    visited+=1
                    if entry['kind']=='directory':
                        if PurePosixPath(entry['path']).name in {'.venv','node_modules','__pycache__','build','dist'}: continue
                        if len(PurePosixPath(entry['path']).parts)<8: pending.append(entry['path'])
                    else:
                        try: text=self.workspace.read(entry['path'])
                        except (OSError,ValueError,UnicodeError): continue
                        for number,line in enumerate(text.splitlines(),1):
                            if query in line:
                                matches.append({'path':entry['path'],'line':number,'text':line[:500]})
                                if len(matches)>=50: break
                    if visited>=500 or len(matches)>=50: break
            return json.dumps(matches,ensure_ascii=False)
        @tool
        def write_file(path: str, content: str) -> dict:
            """Create or replace a workspace file; user permission required. Parent must exist."""
            return self.workspace.write(path,content)
        @tool
        def edit_file(path: str, old_text: str, new_text: str) -> dict:
            """Replace exactly one literal occurrence in workspace file; user permission required."""
            text=self.workspace.read(path)
            if not old_text or text.count(old_text)!=1:
                raise ValueError('old_text must match exactly once; read file and retry')
            return self.workspace.write(path,text.replace(old_text,new_text,1))
        @tool
        def bash(command: str, timeout: int = 10) -> dict:
            """Run Bash in workspace, requiring permission every call; NOT an OS sandbox. Max 30s."""
            return run_bash(command,cwd=self.workspace.root,timeout=timeout)
        @tool
        def python(code: str, data: dict | None = None) -> str:
            """Run bounded Python subset in Monty; final expression is returned. No files/network/host functions. Optional data dict is available as data. No pip or CPython."""
            captured=run_monty(code,inputs={'data':data or {}},capture_output=True)
            result=captured if captured['stdout'] else captured['result']
            return bounded_json(result,limit=12000,default=str,truncate=True)
        self.tools=[read_file,list_files,search_files,write_file,edit_file,bash,python]
        self.by_name={item.name:item for item in self.tools}

    def validate(self, call):
        name=call['name']
        if name not in self.by_name: raise ValueError('Unknown tool')
        args=self.by_name[name].args_schema.model_validate(call['args']).model_dump()
        # Do not silently discard extra arguments from an untrusted tool request.
        if set(call['args'])-set(args): raise ValueError('Unknown tool arguments')
        if name in {'read_file','edit_file','write_file'}:
            self.workspace.check(args['path'],write=name=='write_file')
        elif name in {'list_files','search_files'}:
            self.workspace.check(args['path'],directory=True)
        if name=='bash' and (not args['command'].strip() or len(args['command'])>20000 or not 0<args['timeout']<=30):
            raise ValueError('Invalid Bash command or timeout')
        if name=='python' and len(args['code'].encode())>20000: raise ValueError('Python source too large')
        if name=='write_file' and len(args['content'].encode())>1024*1024: raise ValueError('Write too large')
        return name in {'bash','write_file','edit_file'}
