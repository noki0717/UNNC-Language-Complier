# UNNC DSL Compiler (Algorithm Pseudocode Interpreter)

一个功能完整的伪代码编译器和解释器，支持算法描述语言（DSL）的解析、编译和执行。支持二叉树、列表、if/while/for 循环等复杂数据结构和控制流。

## 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [支持的 DSL 语法](#支持的-dsl-语法)
- [文件格式](#文件格式)
- [使用示例](#使用示例)
- [命令行参数](#命令行参数)
- [内置函数](#内置函数)
- [输出格式](#输出格式)

## 功能特性

✅ **核心语言支持**
- 完整的伪代码算法定义（`Algorithm: Name(params)`）
- 支持行号或无行号的伪代码格式
- 条件语句：`if/elseif/else/endif`
- 循环语句：`while/endwhile`、`for...from...to/endfor`、`for...in...list/endfor`
- 变量赋值：`let x = value` 或 `x ← value`
- 函数调用：支持递归和嵌套调用
- 返回语句：`return value`

✅ **数据结构**
- **列表**：使用 `cons` 构建，`isEmpty/value/tail` 操作
- **二叉树**：使用 `node(left, x, right)` 构建，`leaf` 叶子节点
- **树操作**：`isLeaf/root/left/right/size` 函数

✅ **高级特性**
- 美化的树形结构可视化输出
- 自动去除输出中的 null 值
- 支持多个函数执行，分行显示结果
- 变量赋值与后续算法调用
- 错误捕获与详细错误报告
- 多种输入格式支持

## 快速开始

### 最简单的方式

将以下文件放在同一目录：
1. `UNNC language complier.py` - 编译器脚本
2. `algorithm.txt` - 你的伪代码算法
3. `input.in` - 输入的测试用例

然后运行：
```bash
python "UNNC language complier.py"
```

脚本会自动：
- 读取 `algorithm.txt` 中的所有算法
- 执行 `input.in` 中的所有测试用例
- 生成 `output.out` 输出文件
- 生成辅助文件：`case_1.json`、`case_2.json` 等

### 示例项目结构

```
my_project/
├── UNNC language complier.py  # 编译器（放在这里）
├── algorithm.txt              # 算法定义
├── input.in                   # 测试用例输入
└── output.out                 # 生成的输出文件
```

## 支持的 DSL 语法

### 1. 算法定义

```
Algorithm: AlgorithmName(param1, param2)
Requires: 参数描述（可选，会被忽略）
Returns: 返回值描述（可选，会被忽略）

1: statement 1
2: statement 2
...
```

**注意**：行号是可选的，以下两种格式都支持：
```
with line numbers:     1: let x = 5
without line numbers:  let x = 5
```

### 2. 条件语句

```
if condition then
    statements...
elseif condition2 then
    statements...
else
    statements...
endif
```

### 3. while 循环

```
while condition do
    statements...
endwhile
```

### 4. for 循环

**格式 1：从-到循环**
```
for i from 1 to 10 do
    statements...
endfor
```

**格式 2：列表迭代**
```
for item in list do
    statements...
endfor
```

### 5. 变量赋值

```
let x = expression       # 推荐
x ← expression          # 备选
```

### 6. 返回语句

```
return expression
return                  # 返回 None
```

### 7. 表达式

支持：
- 算术运算：`+, -, *, /, %`
- 比较：`<, <=, >, >=, ==, !=`
- 逻辑：`and, or, not`
- 函数调用：`func(arg1, arg2)`
- 变量引用：`variable_name`

## 文件格式

### algorithm.txt - 伪代码文件

```
Algorithm: CountWays(N)
Requires: Non-negative integer N
Returns: Number of ways to express N as sum of positive integers

if N <= 0 then
    return 0
endif

if N == 1 then
    return 1
endif

let count = 0
for i from 1 to N - 1 do
    let count = count + CountWays(N - i)
endfor

return count
```

### input.in - 输入文件

支持多种格式（混合使用）：

**格式 1：函数调用 (推荐)**
```
CountWays(5)
CountWays(10)
```

**格式 2：带冒号的简短语法**
```
AlgoName:arg1,arg2
SumList:1,2,3
```

**格式 3：变量赋值**
```
T = node(
    node(node(leaf,10,leaf),20,node(leaf,25,leaf)),
    30,
    node(leaf,40,leaf)
)
```

**格式 4：使用 JSON（复杂参数）**
```json
{"algo": "SumList", "args": [[1,2,3,4,5]]}
```

**格式 5：引用外部 JSON 文件**
```
@case_1.json
```

**格式 6：注释**
```
# This is a comment
CountWays(5)  # This will be executed
```

### output.out - 输出文件

JSON 格式，包含：
- 单个非列表结果：直接输出值
- 多个结果：每行一个
- 错误信息：`{"error": "error message"}`
- 树形结构：JSON 序列化 + 可视化

示例：
```json
3
[[45], [17, 15, 13], [13, 11, 9, 7, 5]]
```

## 使用示例

### 示例 1：基本算法执行

**algorithm.txt:**
```
Algorithm: Sum(N)

if N <= 0 then
    return 0
else
    return N + Sum(N - 1)
endif
```

**input.in:**
```
Sum(5)
Sum(10)
```

**运行：**
```bash
python "UNNC language complier.py"
```

**output.out:**
```
15
55
```

---

### 示例 2：二叉树操作

**algorithm.txt:**
```
Algorithm: FindMax(T)

if isLeaf(T) then
    return -1
endif

let right_max = FindMax(right(T))
let current = root(T)

if right_max > current then
    return right_max
else
    return current
endif
```

**input.in:**
```
T = node(
    node(node(leaf,10,leaf),20,node(leaf,25,leaf)),
    30,
    node(leaf,40,leaf)
)
FindMax(T)
```

**运行：**
```bash
python "UNNC language complier.py"
```

**output.out:**
```
40

--- Tree Visualization ---

Case 1:
            30
           /  \
         20    40
        / \
       10 25
```

---

### 示例 3：列表操作

**algorithm.txt:**
```
Algorithm: SumList(L)

if isEmpty(L) then
    return 0
endif

return value(L) + SumList(tail(L))

Algorithm: CountElements(L)

if isEmpty(L) then
    return 0
endif

return 1 + CountElements(tail(L))
```

**input.in:**
```
SumList([1,2,3,4,5])
CountElements([10,20,30])
```

---

### 示例 4：for 循环

**algorithm.txt:**
```
Algorithm: RangeSum(N)

let result = 0
for i from 1 to N do
    let result = result + i
endfor

return result

Algorithm: ListDouble(L)

let result = Nil
for item in L do
    let result = cons(item * 2, result)
endfor

return result
```

**input.in:**
```
RangeSum(10)
ListDouble([1,2,3])
```

## 命令行参数

```bash
python "UNNC language complier.py" [options]
```

### 选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `--src FILE` | 指定伪代码文件路径 | `--src my_algo.txt` |
| `--in FILE` | 指定输入文件路径 | `--in cases.in` |
| `--out FILE` | 指定输出文件路径 | `--out result.out` |
| `--exec CASE` | 执行单个测试用例（可重复） | `--exec "Sum(5)"` |
| `--show-list` | 显示 DSL 列表结果 | 无参数 |
| `--generate` | 生成 case JSON 文件 | 无参数 |

### 使用示例

```bash
# 基本执行
python "UNNC language complier.py"

# 指定源文件和输入
python "UNNC language complier.py" --src algorithms.txt --in test_cases.in

# 单个测试用例
python "UNNC language complier.py" --src algorithms.txt --exec "Sum(10)"

# 多个测试用例
python "UNNC language complier.py" --src algorithms.txt --exec "Sum(5)" --exec "Sum(10)"

# 显示列表结果
python "UNNC language complier.py" --src algorithms.txt --show-list

# 自定义输出文件
python "UNNC language complier.py" --src algorithms.txt --out my_results.json
```

## 内置函数

### 列表函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `cons(x, L)` | 将元素 x 加入列表 L 的头部 | `cons(1, L)` |
| `isEmpty(L)` | 检查列表是否为空 | `isEmpty(L)` |
| `value(L)` | 获取列表的第一个元素 | `value(L)` |
| `tail(L)` | 获取列表除第一个元素外的部分 | `tail(L)` |
| `merge(L1, L2)` | 合并两个列表 | `merge(L1, L2)` |
| `Nil` | 空列表 | `Nil` |

### 树函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `node(left, x, right)` | 创建二叉树节点 | `node(leaf, 5, leaf)` |
| `isLeaf(t)` | 检查是否为叶子节点 | `isLeaf(t)` |
| `root(t)` | 获取节点的值 | `root(t)` |
| `left(t)` | 获取左子树 | `left(t)` |
| `right(t)` | 获取右子树 | `right(t)` |
| `size(t)` | 计算树的节点个数 | `size(t)` |
| `leaf` | 叶子节点常量 | `leaf` |

## 输出格式

### 单一非列表输出
```
3
```

### 多个输出（按行分隔）
```
10
[1, 2, 3]
55
```

### 包含树结构的输出

JSON 部分：
```json
{"_type": "node", "left": {...}, "value": 5, "right": {...}}
```

树形可视化：
```
            50
           /  \
         30    70
        / \   / \
       20 40 60 80
      / \       \
    10 25       65
```

### 错误输出
```json
{"error": "Unknown function: foo"}
```

## 常见问题

### Q: 为什么输出中有很多 null？
**A:** `Nil`（空列表）在 JSON 中序列化为 `null`。编译器会自动过滤列表中的 `null` 值以保持输出清洁。

### Q: 我的算法为什么返回 None？
**A:** 
- 算法没有 `return` 语句时返回 `None`
- 变量赋值语句不会产生输出

### Q: 如何处理复杂的嵌套树结构？
**A:** 使用多行格式：
```
T = node(
    node(leaf, 10, leaf),
    20,
    node(leaf, 30, leaf)
)
```

### Q: 支持哪些运算符？
**A:** 支持标准数学和逻辑运算符：
- 算术：`+, -, *, /, %`
- 比较：`<, <=, >, >=, ==, !=`
- 逻辑：`and, or, not`

### Q: 如何调试我的算法？
**A:** 
- 查看 `output.out` 中的错误信息
- 使用 `--exec` 参数逐个测试函数
- 启用详细输出查看执行过程

## 技术细节

### 架构

```
┌─────────────────┐
│  Input Files    │
│  (algorithm.txt)│
│  (input.in)     │
└────────┬────────┘
         │
    ┌────▼─────────┐
    │  Compiler    │
    │ (compile_unnc)
    └────┬─────────┘
         │
    ┌────▼──────────────┐
    │  Env (Runtime)    │
    │ - funcs           │
    │ - globals         │
    │ - builtins        │
    └────┬──────────────┘
         │
    ┌────▼─────────────┐
    │  Executor        │
    │ - eval_expr      │
    │ - run_lines      │
    └────┬─────────────┘
         │
    ┌────▼───────────┐
    │  Output Files  │
    │ (output.out)   │
    └────────────────┘
```

### 核心组件

1. **Compiler** (`compile_unnc`)
   - 解析伪代码文本
   - 提取算法定义
   - 注册到运行时环境

2. **Runtime** (`Env` class)
   - 管理函数定义
   - 管理全局变量
   - 提供内置函数

3. **Executor** (`execute_algorithm`)
   - 解释执行算法
   - 处理控制流（if/while/for）
   - 管理局部变量作用域

4. **Expression Evaluator** (`eval_expr`)
   - 解析和求值表达式
   - 支持函数调用
   - 支持变量引用

## 扩展和自定义

### 添加新的内置函数

编辑 `Env.__init__` 方法中的 `builtins` 字典：

```python
self.builtins['my_function'] = my_function_impl
```

### 添加新的语言特性

修改 `run_lines` 函数中的处理逻辑以支持新的语句类型。

## 系统要求

- Python 3.6+
- 无第三方依赖

## 许可证

MIT License

## 作者

UNNC Language Compiler Team

## 更新日志

### v1.0.0 (2025-12-01)
- ✅ 基础伪代码编译器
- ✅ if/while/for 循环支持
- ✅ 二叉树和列表数据结构
- ✅ 树形可视化输出
- ✅ 多种输入格式支持
- ✅ 错误捕获和详细报告
- ✅ 英文注释完整化
- ✅ 多个函数执行分行显示
- ✅ 支持变量赋值与全局作用域
