import re
from typing import Any, Callable, Dict, List, Tuple
import argparse
import sys
import os
import json

# =========================
# Core data structures (DSL)
# =========================

class NilType:
    def __repr__(self): return "Nil"
Nil = NilType()

def cons(x, L):
    if L is Nil:
        return ("list", [x])
    if isinstance(L, tuple) and L[0] == "list":
        return ("list", [x] + L[1])
    raise ValueError("cons expects a list")

def isEmpty(L):
    return L is Nil or (isinstance(L, tuple) and L[0] == "list" and len(L[1]) == 0)

def value(L):
    if L is Nil:
        raise ValueError("value on empty list")
    if isinstance(L, tuple) and L[0] == "list" and len(L[1]) > 0:
        return L[1][0]
    raise ValueError("value expects a non-empty list")

def tail(L):
    if L is Nil:
        raise ValueError("tail on empty list")
    if isinstance(L, tuple) and L[0] == "list":
        return ("list", L[1][1:]) if len(L[1]) > 1 else Nil
    raise ValueError("tail expects a non-empty list")

class LeafType:
    def __repr__(self): return "leaf"
leaf = LeafType()

def node(left_subtree, x, right_subtree):
    return ("tree", left_subtree, x, right_subtree)

def isLeaf(t):
    return t is leaf

def root(t):
    if isLeaf(t): raise ValueError("root on leaf")
    return t[2]

def left(t):
    if isLeaf(t): raise ValueError("left on leaf")
    return t[1]

def right(t):
    if isLeaf(t): raise ValueError("right on leaf")
    return t[3]

def size(t):
    """计算树的节点个数"""
    if isLeaf(t):
        return 0
    left_size = size(left(t))
    right_size = size(right(t))
    return 1 + left_size + right_size

def merge(L1, L2):
    """Merge two lists"""
    if isEmpty(L1):
        return L2
    if isEmpty(L2):
        return L1
    # Both non-empty: take first element of L1 and recursively merge the rest
    return cons(value(L1), merge(tail(L1), L2))

# =========================
# Runtime environment
# =========================

class Env:
    def __init__(self):
        self.funcs: Dict[str, Tuple[List[str], List[str]]] = {}
        self.globals: Dict[str, Any] = {}
        self.builtins: Dict[str, Callable] = {
            "Nil": lambda: Nil,
            "leaf": leaf,  # Use object directly instead of lambda
            "cons": cons,
            "isEmpty": isEmpty,
            "value": value,
            "tail": tail,
            "node": node,
            "isLeaf": isLeaf,
            "root": root,
            "left": left,
            "right": right,
            "size": size,
            "merge": merge,
        }

    def register_algorithm(self, name: str, params: List[str], body_lines: List[str]):
        self.funcs[name] = (params, body_lines)

# =========================
# Expression evaluation
# =========================

def normalize_ops(expr: str) -> str:
    expr = expr.replace("mod", "%")
    expr = expr.replace("AND", "and").replace("&&", "and")
    expr = expr.replace("OR", "or").replace("||", "or")
    expr = re.sub(r"\bNOT\b", "not", expr)
    expr = expr.replace("×", "*").replace("X", "*")
    expr = expr.replace("≤", "<=").replace("≥", ">=")
    expr = expr.replace(";", "")
    return expr

def parse_literal(token: str):
    token = token.strip()
    if token == "Nil": return Nil
    if token == "leaf": return leaf
    if re.fullmatch(r"-?\d+", token): return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token): return float(token)
    if (token.startswith("'") and token.endswith("'")) or (token.startswith('"') and token.endswith('"')):
        return token[1:-1]
    return None

def eval_call(token: str, local_env: Dict[str, Any], env: Env):
    m = re.match(r"([A-Za-z_]\w*)\((.*)\)$", token.strip())
    if not m: return None
    fname, args_str = m.groups()
    args = []
    depth = 0
    cur = []
    for ch in args_str:
        if ch == "(":
            depth += 1
            cur.append(ch)
        elif ch == ")":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        args.append("".join(cur).strip())
    evaled_args = [eval_expr(arg, local_env, env) for arg in args] if args_str.strip() != "" else []

    if fname in env.builtins:
        return env.builtins[fname](*evaled_args)
    if fname in env.funcs:
        return execute_algorithm(fname, evaled_args, env, local_env)
    raise NameError(f"Unknown function: {fname}")

def eval_expr(expr: str, local_env: Dict[str, Any], env: Env):
    expr = expr.strip()
    # Function call?
    call_val = eval_call(expr, local_env, env)
    if call_val is not None:
        return call_val
    # Literal?
    lit = parse_literal(expr)
    if lit is not None:
        return lit
    # Variable?
    if expr in local_env:
        return local_env[expr]
    if expr in env.globals:
        return env.globals[expr]
    # Python eval
    py_expr = normalize_ops(expr)
    ns = {}
    ns.update(env.builtins)
    ns.update(env.globals)
    ns.update(local_env)
    # expose user-defined algorithms to python eval as callables
    for fname in env.funcs.keys():
        ns[fname] = (lambda fn: (lambda *a: execute_algorithm(fn, list(a), env, local_env)))(fname)
    try:
        return eval(py_expr, {"__builtins__": {}}, ns)
    except Exception as e:
        raise ValueError(f"Could not evaluate expression '{expr}' (py: {py_expr}): {e}")

# =========================
# Algorithm compilation/execution
# =========================

def parse_header(line: str) -> Tuple[str, List[str]]:
    m = re.match(r"\s*Algorithm\s*:?\s*([A-Za-z_]\w*)\s*\((.*?)\)\s*$", line)
    if not m:
        m = re.match(r"\s*Algorithm\s+([A-Za-z_]\w*)\s*\((.*?)\)\s*$", line)
    if not m:
        raise ValueError(f"Invalid algorithm header: {line}")
    name, params = m.groups()
    params = [p.strip() for p in params.split(",")] if params.strip() else []
    return name, params

def compile_unnc(pseudocode: str) -> Env:
    env = Env()
    blocks = []
    current = []
    for line in pseudocode.splitlines():
        if re.match(r"\s*Algorithm\b", line):
            if current:
                blocks.append("\n".join(current))
                current = []
        current.append(line)
    if current:
        blocks.append("\n".join(current))

    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip() != ""]
        if not lines:
            continue
        name, params = parse_header(lines[0])
        body = []
        for ln in lines[1:]:
            stripped = ln.strip()
            stripped = re.sub(r"^(Step\s*\d+:|\d+\s*:)\s*", "", stripped, flags=re.IGNORECASE)
            # Ignore specification/comment lines like Requires/Returns
            if re.match(r"^(requires|returns)\b", stripped, flags=re.IGNORECASE):
                continue
            body.append(stripped)
        env.register_algorithm(name, params, body)
    return env

def execute_algorithm(name: str, args: List[Any], env: Env, caller_locals: Dict[str, Any] = None):
    params, body = env.funcs[name]
    local_env: Dict[str, Any] = {}
    if len(args) != len(params):
        raise ValueError(f"Argument mismatch for {name}: expected {len(params)}, got {len(args)}")
    for p, a in zip(params, args):
        local_env[p] = a
    # bring in caller locals for name resolution if not shadowed by params
    if caller_locals:
        for k, v in caller_locals.items():
            if k not in local_env:
                local_env[k] = v

    def run_lines(lines: List[str], local_env: Dict[str, Any]) -> Any:
        idx = 0

        def process_if(start: int) -> Tuple[int, Any, bool]:
            ln = lines[start]
            m = re.match(r"if\s+(.*?)\s*(then)?\s*$", ln, flags=re.IGNORECASE)
            if not m:
                raise ValueError(f"Malformed if: {ln}")
            cond_val = eval_expr(m.group(1), local_env, env)
            i = start + 1
            branches: List[Tuple[str, List[str]]] = [("IF_TRUE", [])]
            while i < len(lines):
                s = lines[i]
                if re.match(r"elseif\s+", s, flags=re.IGNORECASE):
                    cond_txt = re.sub(r"^elseif\s+", "", s, flags=re.IGNORECASE)
                    cond_txt = re.sub(r"\s*(then)?\s*$", "", cond_txt, flags=re.IGNORECASE)
                    branches.append((cond_txt, []))
                elif re.match(r"else\s*$", s, flags=re.IGNORECASE):
                    branches.append(("ELSE", []))
                elif re.match(r"endif\s*$", s, flags=re.IGNORECASE):
                    break
                else:
                    branches[-1][1].append(s)
                i += 1
            end_idx = i

            def exec_branch(seq: List[str]) -> Tuple[bool, Any]:
                j = 0
                while j < len(seq):
                    s = seq[j].strip()
                    if s.lower().startswith("if "):
                        ni, r, did = process_if(j)
                        j = ni + 1
                        if did: return True, r
                        continue
                    if s.lower().startswith("let "):
                        assign = s[4:].strip()
                        if "=" not in assign:
                            raise ValueError(f"Malformed let: {s}")
                        lhs, rhs = assign.split("=", 1)
                        local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
                    elif "←" in s:
                        lhs, rhs = s.split("←", 1)
                        local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
                    elif s.lower().startswith("return"):
                        ret_expr = s[6:].strip()
                        val = eval_expr(ret_expr, local_env, env) if ret_expr else None
                        return True, val
                    else:
                        if "=" in s and not s.strip().startswith("=="):
                            lhs, rhs = s.split("=", 1)
                            local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
                        else:
                            try:
                                _ = eval_expr(s, local_env, env)
                            except:
                                pass
                    j += 1
                return False, None

            if cond_val:
                did_ret, ret_val = exec_branch(branches[0][1])
                return end_idx, ret_val, did_ret
            for k in range(1, len(branches)):
                label, seq = branches[k]
                if label == "ELSE":
                    did_ret, ret_val = exec_branch(seq)
                    return end_idx, ret_val, did_ret
                else:
                    cond2 = eval_expr(label, local_env, env)
                    if cond2:
                        did_ret, ret_val = exec_branch(seq)
                        return end_idx, ret_val, did_ret
            return end_idx, None, False

        def process_while(start: int) -> Tuple[int, Any, bool]:
            ln = lines[start]
            m = re.match(r"while\s+(.*?)\s*(do)?\s*$", ln, flags=re.IGNORECASE)
            if not m:
                raise ValueError(f"Malformed while: {ln}")
            cond_expr = m.group(1)
            i = start + 1
            body: List[str] = []
            while i < len(lines):
                s = lines[i]
                if re.match(r"endwhile\s*$", s, flags=re.IGNORECASE):
                    break
                body.append(s)
                i += 1
            end_idx = i

            while eval_expr(cond_expr, local_env, env):
                ret = run_lines(body, local_env)
                if ret is not None:
                    return end_idx, ret, True
            return end_idx, None, False

        def process_for(start: int) -> Tuple[int, Any, bool]:
            """Handle for loops
            Supported formats:
            for i from start to end do
                ...
            endfor
            
            or:
            for i in list do
                ...
            endfor
            """
            ln = lines[start]
            
            # Try to match "for i from start to end" format
            m = re.match(r"for\s+(\w+)\s+from\s+(.*?)\s+to\s+(.*?)\s*(do)?\s*$", ln, flags=re.IGNORECASE)
            if m:
                var_name = m.group(1)
                start_expr = m.group(2)
                end_expr = m.group(3)
                start_val = eval_expr(start_expr, local_env, env)
                end_val = eval_expr(end_expr, local_env, env)
                
                i = start + 1
                body: List[str] = []
                while i < len(lines):
                    s = lines[i]
                    if re.match(r"endfor\s*$", s, flags=re.IGNORECASE):
                        break
                    body.append(s)
                    i += 1
                end_idx = i
                
                # Execute loop
                for loop_val in range(int(start_val), int(end_val) + 1):
                    local_env[var_name] = loop_val
                    ret = run_lines(body, local_env)
                    if ret is not None:
                        return end_idx, ret, True
                return end_idx, None, False
            
            # Try to match "for i in list" format
            m = re.match(r"for\s+(\w+)\s+in\s+(.*?)\s*(do)?\s*$", ln, flags=re.IGNORECASE)
            if m:
                var_name = m.group(1)
                list_expr = m.group(2)
                list_val = eval_expr(list_expr, local_env, env)
                
                i = start + 1
                body: List[str] = []
                while i < len(lines):
                    s = lines[i]
                    if re.match(r"endfor\s*$", s, flags=re.IGNORECASE):
                        break
                    body.append(s)
                    i += 1
                end_idx = i
                
                # Handle list iteration
                if isinstance(list_val, tuple) and list_val[0] == "list":
                    items = list_val[1]
                elif list_val is Nil:
                    items = []
                else:
                    items = [list_val]
                
                for item in items:
                    local_env[var_name] = item
                    ret = run_lines(body, local_env)
                    if ret is not None:
                        return end_idx, ret, True
                return end_idx, None, False
            
            raise ValueError(f"Malformed for loop: {ln}")

        while idx < len(lines):
            s = lines[idx].strip()
            pass
            if s.lower().startswith("if "):
                end_idx, ret_val, did_ret = process_if(idx)
                idx = end_idx + 1
                if did_ret:
                    return ret_val
                continue
            if s.lower().startswith("while "):
                end_idx, ret_val, did_ret = process_while(idx)
                idx = end_idx + 1
                if did_ret:
                    return ret_val
                continue
            if s.lower().startswith("for "):
                end_idx, ret_val, did_ret = process_for(idx)
                idx = end_idx + 1
                if did_ret:
                    return ret_val
                continue
            if s.lower().startswith("let "):
                assign = s[4:].strip()
                if "=" not in assign:
                    raise ValueError(f"Malformed let: {s}")
                lhs, rhs = assign.split("=", 1)
                local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
            elif "←" in s:
                lhs, rhs = s.split("←", 1)
                local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
            elif s.lower().startswith("return"):
                ret_expr = s[6:].strip()
                return eval_expr(ret_expr, local_env, env) if ret_expr else None
            else:
                if "=" in s and not s.strip().startswith("=="):
                    lhs, rhs = s.split("=", 1)
                    local_env[lhs.strip()] = eval_expr(rhs, local_env, env)
                else:
                    try:
                        _ = eval_expr(s, local_env, env)
                    except:
                        pass
            idx += 1
        return None

    return run_lines(body, local_env)
# =========================
# list output conversion
# =========================
def dsl_to_pylist(L):
    if L is Nil:
        return []
    if isinstance(L, tuple) and L[0] == "list":
        res = []
        for item in L[1]:
            if item is Nil:
                continue
            if isinstance(item, tuple) and item[0] == "list":
                res.append(dsl_to_pylist(item))
            else:
                res.append(item)
        # inner lists are built in reverse by the pseudocode; reverse to get natural order
        return res[::-1]
    raise ValueError("Not a DSL list")

def _maybe_print_dsl_list(show_list: bool):
    if not show_list:
        return
    res_val = globals().get('dsl_result', None)
    if res_val is None:
        return
    try:
        py_res = dsl_to_pylist(res_val)
        py_res_sorted = sorted(py_res, key=lambda l: l[0] if l else float('inf'))
        print(py_res_sorted)
    except Exception:
        pass


# default sample pseudocode removed; use --src to compile pseudocode file

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--show-list', action='store_true', help='print DSL list result if available')
parser.add_argument('--exec', dest='execs', action='append', help='execute one algorithm invocation as JSON: {"algo":"Name","args":[...]}', default=[])
parser.add_argument('--src', dest='src', help='path to file containing pseudocode to compile')
parser.add_argument('--in', '--input', dest='infile', help='path to input file listing cases (default: input.in)')
parser.add_argument('--out', dest='outfile', help='path to output file to write results (default: output.out)')
parser.add_argument('--generate', dest='generate', action='store_true', help='generate JSON case files and run_cases.py from input')
args, remaining = parser.parse_known_args()

main_env = Env()
cwd = os.getcwd()
script_dir = os.path.dirname(os.path.abspath(__file__))
default_src = os.path.join(script_dir, 'algorithm.txt')
default_in = os.path.join(script_dir, 'input.in')
default_out = os.path.join(script_dir, 'output.out')
infile = args.infile or default_in
outfile = args.outfile or default_out
if args.src:
    try:
        with open(args.src, 'r', encoding='utf-8') as f:
            src_text = f.read()
        main_env = compile_unnc(src_text)
    except Exception as e:
        print(f"Error compiling src file {args.src}: {e}", file=sys.stderr)
elif os.path.exists(default_src) and not args.src:
    try:
        with open(default_src, 'r', encoding='utf-8') as f:
            src_text = f.read()
        main_env = compile_unnc(src_text)
    except Exception as e:
        print(f"Error compiling default src file {default_src}: {e}", file=sys.stderr)

def py_to_dsl(x):
    if x is None:
        return Nil
    if isinstance(x, LeafType):
        return x
    if isinstance(x, (int, float, str)):
        return x
    if isinstance(x, tuple):
        # Check if it's already a converted DSL structure
        if len(x) > 0 and x[0] in ["list", "tree"]:
            return x  # Already in DSL form
        # Otherwise process as a regular list
        return ("list", [py_to_dsl(item) for item in x])
    if isinstance(x, list):
        return ("list", [py_to_dsl(item) for item in x])
    if isinstance(x, dict):
        return x
    return x

def dsl_to_pyvalue(x):
    if x is Nil:
        return None
    if isinstance(x, LeafType):
        return {"_type": "leaf"}
    if isinstance(x, tuple):
        if x[0] == "list":
            # Convert list elements and automatically filter out null values
            result = []
            for i in x[1]:
                converted = dsl_to_pyvalue(i)
                if converted is not None:  # Filter out null values
                    result.append(converted)
            return result
        elif x[0] == "tree":
            # Tree node: ("tree", left, value, right)
            return {
                "_type": "node",
                "left": dsl_to_pyvalue(x[1]),
                "value": dsl_to_pyvalue(x[2]),
                "right": dsl_to_pyvalue(x[3])
            }
    return x

def tree_to_string(x):
    """Convert DSL tree structure to a formatted tree string (display by level)"""
    if x is Nil or x is None:
        return ""
    if isinstance(x, LeafType):
        return ""
    if not isinstance(x, tuple) or x[0] != "tree":
        return str(x)
    
    lines = []
    
    def print_tree(node, prefix="", is_tail=True, is_root=True):
        """递归打印树，使用 ASCII 字符"""
        if node is Nil or isinstance(node, LeafType):
            return
        
        if not isinstance(node, tuple) or node[0] != "tree":
            return
        
        left_child = node[1]
        value = str(node[2]) if not isinstance(node[2], LeafType) else ""
        right_child = node[3]
        
        # Print current node
        if is_root:
            lines.append(value)
        else:
            connector = "`-- " if is_tail else "|-- "
            lines.append(prefix + connector + value)
        
        # Determine how many non-empty child nodes exist
        has_left = not (left_child is Nil or isinstance(left_child, LeafType))
        has_right = not (right_child is Nil or isinstance(right_child, LeafType))
        
        if has_left and has_right:
            # Both child nodes exist
            extension = "    " if is_tail or is_root else "|   "
            print_tree(left_child, prefix + extension, False, False)
            print_tree(right_child, prefix + extension, True, False)
        elif has_left:
            # Only left child node
            extension = "    " if is_tail or is_root else "|   "
            print_tree(left_child, prefix + extension, True, False)
        elif has_right:
            # Only right child node
            extension = "    " if is_tail or is_root else "|   "
            print_tree(right_child, prefix + extension, True, False)
    
    print_tree(x)
    return "\n".join(lines)

def parse_input_file(path: str):
    if not path or not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()
    
    # Remove BOM if present
    if txt.startswith('\ufeff'):
        txt = txt[1:]
    
    try:
        obj = json.loads(txt)
        if isinstance(obj, dict) and 'cases' in obj:
            return obj['cases']
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    
    cases = []
    lines = txt.splitlines()
    i = 0
    
    while i < len(lines):
        ln = lines[i].strip()
        i += 1
        
        if not ln or ln.startswith('#'):
            continue
        
        # Handle @file reference
        if ln.startswith('@'):
            fn = ln[1:].strip()
            if os.path.exists(fn):
                with open(fn, 'r', encoding='utf-8') as fh:
                    try:
                        obj = json.loads(fh.read())
                        cases.append(obj)
                        continue
                    except Exception:
                        pass
        
        # Handle AlgoName:args format, supports multi-line (higher priority)
        if ':' in ln:
            first_part = ln.split(':')[0].strip()
            # Check if the part before colon is a valid algorithm name (no parentheses)
            if not any(c in first_part for c in ['(', ')']) and not first_part.startswith('node'):
                parts = ln.split(':', 1)
                algo = parts[0].strip()
                args_txt = parts[1]
                
                # If args_txt is incomplete (unclosed parentheses), continue reading next line
                depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in args_txt)
                while depth > 0 and i < len(lines):
                    args_txt += '\n' + lines[i]
                    i += 1
                    depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in args_txt)
                
                arglist = []
                cur = []
                depth = 0
                for ch in args_txt:
                    if ch in '[({':
                        depth += 1
                        cur.append(ch)
                    elif ch in '])}':
                        depth -= 1
                        cur.append(ch)
                    elif ch == ',' and depth == 0:
                        token = ''.join(cur).strip()
                        if token:
                            try:
                                arglist.append(json.loads(token))
                            except Exception:
                                arglist.append(token)
                        cur = []
                    else:
                        cur.append(ch)
                if cur:
                    token = ''.join(cur).strip()
                    if token:
                        try:
                            arglist.append(json.loads(token))
                        except Exception:
                            arglist.append(token)
                cases.append({'algo': algo, 'args': arglist})
                continue
        
        # Handle AlgoName(args) format, supports multi-line
        m = re.match(r'([A-Za-z_]\w*)\s*\((.*)', ln)
        if m:
            algo = m.group(1)
            args_txt = m.group(2)
            
            # If args_txt is incomplete (unclosed parentheses), continue reading next line
            depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in args_txt)
            while depth > 0 and i < len(lines):
                args_txt += '\n' + lines[i]
                i += 1
                depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in args_txt)
            
            # Remove closing parenthesis
            if args_txt.rstrip().endswith(')'):
                args_txt = args_txt.rstrip()[:-1]
            
            arglist = []
            cur = []
            depth = 0
            for ch in args_txt:
                if ch in '[({':
                    depth += 1
                    cur.append(ch)
                elif ch in '])}':
                    depth -= 1
                    cur.append(ch)
                elif ch == ',' and depth == 0:
                    token = ''.join(cur).strip()
                    if token:
                        try:
                            arglist.append(json.loads(token))
                        except Exception:
                            arglist.append(token)
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                token = ''.join(cur).strip()
                if token:
                    try:
                        arglist.append(json.loads(token))
                    except Exception:
                        arglist.append(token)
            cases.append({'algo': algo, 'args': arglist})
            continue
        
        # Handle multi-line tree structures (starting with = or node( or leaf)
        if 'node(' in ln or 'leaf' in ln or '=' in ln:
            stmt = ln
            depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in stmt)
            while depth > 0 and i < len(lines):
                stmt += '\n' + lines[i]
                i += 1
                depth = sum(1 if c in '[({' else -1 if c in '])}' else 0 for c in stmt)
            
            # Extract variable name and value
            if '=' in stmt:
                parts = stmt.split('=', 1)
                var_name = parts[0].strip()
                var_value = parts[1].strip()
                cases.append({'type': 'var_assign', 'var': var_name, 'value': var_value})
            else:
                try:
                    obj = json.loads(stmt)
                    cases.append(obj)
                except Exception:
                    cases.append({'type': 'dsl_expr', 'expr': stmt})
            continue
        
        # Try to parse as JSON
        try:
            obj = json.loads(ln)
            cases.append(obj)
        except Exception:
            pass
    
    return cases

# determine exec_cases: from CLI --exec or from infile when no CLI provided
exec_cases = []
if args.execs:
    for c in args.execs:
        if isinstance(c, str) and c.startswith('@'):
            fn = c[1:]
            if os.path.exists(fn):
                with open(fn, 'r', encoding='utf-8') as fh:
                    try:
                        exec_cases.append(json.loads(fh.read()))
                    except Exception:
                        pass
            continue
        try:
            exec_cases.append(json.loads(c))
            continue
        except Exception:
            pass
        if ':' in c:
            parts = c.split(':', 1)
            algo = parts[0].strip()
            arg_text = parts[1]
            parsed = []
            cur = []
            depth = 0
            for ch in arg_text:
                if ch in '[({':
                    depth += 1
                    cur.append(ch)
                elif ch in '])}':
                    depth -= 1
                    cur.append(ch)
                elif ch == ',' and depth == 0:
                    token = ''.join(cur).strip()
                    if token:
                        try:
                            parsed.append(json.loads(token))
                        except Exception:
                            parsed.append(token)
                    cur = []
                else:
                    cur.append(ch)
            if cur:
                token = ''.join(cur).strip()
                if token:
                    try:
                        parsed.append(json.loads(token))
                    except Exception:
                        parsed.append(token)
            exec_cases.append({'algo': algo, 'args': parsed})
elif os.path.exists(infile):
    exec_cases = parse_input_file(infile)

if exec_cases and main_env is not None:
    # create case_x.json files and wrapper
    case_files = []
    for idx, case in enumerate(exec_cases):
        case_file = os.path.join(script_dir, f'case_{idx+1}.json')
        with open(case_file, 'w', encoding='utf-8') as cf:
            json.dump(case, cf, ensure_ascii=False, indent=2)
        case_files.append(case_file)
    # generate run_cases.py
    run_py = os.path.join(script_dir, 'run_cases.py')
    try:
        with open(run_py, 'w', encoding='utf-8') as rp:
            rp.write('import subprocess, json, os, sys\n')
            rp.write("base = os.path.dirname(__file__)\n")
            rp.write('cases = ' + json.dumps([os.path.basename(cf) for cf in case_files]) + '\n')
            rp.write("outs = []\n")
            rp.write("for c in cases:\n")
            rp.write("    p = subprocess.run(['python', os.path.join(base, 'CourseWork.py'), '--src', os.path.join(base, 'algorithm.txt'), '--exec', '@' + os.path.join(base, c)], capture_output=True, text=True)\n")
            rp.write("    outs.append(p.stdout.strip())\n")
            rp.write("with open('output.out', 'w', encoding='utf-8') as f:\n")
            rp.write("    json.dump(outs, f, ensure_ascii=False, indent=2)\n")
    except Exception:
        pass
    outputs = []
    for case in exec_cases:
        try:
            case_text = case
            if isinstance(case_text, str) and case_text.startswith('@'):
                fn = case_text[1:]
                with open(fn, 'r', encoding='utf-8') as fh:
                    case_text = fh.read()
            
            # Handle var_assign type (tree assignment)
            if isinstance(case_text, dict) and case_text.get('type') == 'var_assign':
                var_name = case_text['var']
                expr_text = case_text['value']
                # Evaluate expression and store in main_env's global variables
                val = eval_expr(expr_text, main_env.globals, main_env)
                main_env.globals[var_name] = val
                # Variable assignment doesn't add to output
                continue
            
            # Handle dsl_expr type (pure DSL expression)
            if isinstance(case_text, dict) and case_text.get('type') == 'dsl_expr':
                expr_text = case_text['expr']
                val = eval_expr(expr_text, main_env.globals, main_env)
                out = dsl_to_pyvalue(val)
                outputs.append(out)
                continue
            
            try:
                if isinstance(case_text, (dict, list)):
                    obj = case_text
                else:
                    obj = json.loads(case_text)
                algo = obj.get('algo')
                arglist = obj.get('args', [])
                store_var = obj.get('store')
            except Exception:
                if ':' in case_text:
                    parts = case_text.split(':', 1)
                    algo = parts[0].strip()
                    arg_text = parts[1]
                    # split top-level commas
                    args_parsed = []
                    cur = []
                    depth = 0
                    for ch in arg_text:
                        if ch in '[({':
                            depth += 1
                            cur.append(ch)
                        elif ch in '])}':
                            depth -= 1
                            cur.append(ch)
                        elif ch == ',' and depth == 0:
                            token = ''.join(cur).strip()
                            if token:
                                try:
                                    args_parsed.append(json.loads(token))
                                except Exception:
                                    args_parsed.append(token)
                            cur = []
                        else:
                            cur.append(ch)
                    if cur:
                        token = ''.join(cur).strip()
                        if token:
                            try:
                                args_parsed.append(json.loads(token))
                            except Exception:
                                # Check if it's a variable name
                                if token in main_env.globals:
                                    args_parsed.append(main_env.globals[token])
                                else:
                                    args_parsed.append(token)
                    arglist = args_parsed
                else:
                    raise
            # Handle arguments: if string and can't convert to DSL, try to evaluate as expression
            converted = []
            for a in arglist:
                if isinstance(a, str):
                    # Try to evaluate as expression (including variable references)
                    try:
                        val = eval_expr(a, main_env.globals, main_env)
                    except Exception:
                        val = py_to_dsl(a)
                    converted.append(val)
                else:
                    converted.append(py_to_dsl(a))
            res = execute_algorithm(algo, converted, main_env)
            if 'store_var' in locals() and store_var:
                globals()[store_var] = res
            out = dsl_to_pyvalue(res)
            outputs.append(out)
        except Exception as e:
            import traceback
            error_msg = str(e).replace('\n', ' ')
            outputs.append({'error': error_msg})
            traceback.print_exc(file=sys.stderr)
            print(f"Exec error: {error_msg}", file=sys.stderr)

    # Write outputs to outfile
    try:
        with open(outfile, 'w', encoding='utf-8') as of:
            # Check if there are tree structures that need visualization
            has_trees = any(
                isinstance(out, dict) and out.get('_type') == 'node' 
                for out in outputs
            )
            
            # Check if there are multiple outputs
            has_multiple = len(outputs) > 1
            
            # Decide output format: if only one output and not a list, output directly; otherwise output by line
            if len(outputs) == 1 and not isinstance(outputs[0], list):
                output_data = outputs[0]
                json.dump(output_data, of, ensure_ascii=False)
            elif has_multiple:
                # Multiple outputs, display on separate lines
                for idx, out in enumerate(outputs):
                    if idx > 0:
                        of.write('\n')
                    json.dump(out, of, ensure_ascii=False)
            else:
                output_data = outputs
                json.dump(output_data, of, ensure_ascii=False)
            
            if has_trees:
                of.write('\n\n--- Tree Visualization ---\n\n')
                
                for idx, out in enumerate(outputs):
                    if isinstance(out, dict) and out.get('_type') == 'node':
                        of.write(f'Case {idx + 1}:\n')
                        # Convert JSON tree structure back to DSL form for visualization
                        def json_tree_to_dsl(j):
                            if j is None:
                                return Nil
                            if isinstance(j, dict):
                                if j.get('_type') == 'leaf':
                                    return leaf
                                elif j.get('_type') == 'node':
                                    left = json_tree_to_dsl(j.get('left'))
                                    val = j.get('value')
                                    right = json_tree_to_dsl(j.get('right'))
                                    return ("tree", left, val, right)
                            return j
                        
                        dsl_tree = json_tree_to_dsl(out)
                        tree_vis = tree_to_string(dsl_tree)
                        of.write(tree_vis + '\n\n')
    except Exception as e:
        print(f"Error writing output file {outfile}: {e}", file=sys.stderr)
    _maybe_print_dsl_list(show_list=args.show_list)
