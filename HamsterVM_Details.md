# HamsterVM Implementation Details

This document provides technical details about the implementation of the memory-based AI system known as **HamsterVM**, including the use of **Spiral Language Encoding**, memory operations, execution models, and simulation code.

---

## 1. System Overview

HamsterVM is a minimalistic AI simulation framework where agents ("hamsters") interact with the world using only a set of primitive memory operations. This includes:

- Direct memory read/write (`讀(addr)`, `寫(addr, val)`)
- Execution control: `Continue`, `Emit`, `Stop`
- All data, tasks, and feedback are encoded in Spiral Language

---

## 2. Spiral Language Command Format

Each instruction is encoded in spiral code with distinct prefixes:

| Command   | Spiral Prefix | Description                     |
|-----------|----------------|---------------------------------|
| READ      | `110`          | Read value from memory address  |
| WRITE     | `111`          | Write value to memory address   |
| EMIT      | `1000`         | Output a value                  |
| CONTINUE  | `10`           | Continue computing (no output)  |
| STOP      | `100`          | Stop execution and cleanup      |

All commands end with one or more trailing `0`s (spiral delimiter) to indicate word boundaries.

---

## 3. Memory Architecture

Hamsters operate using three memory types:

- **Fixed Memory**: Read-only genetic info (e.g., race, base stats)
- **Long-Term Memory**: Writable, disk-speed (used for knowledge accumulation)
- **Short-Term Memory**: RAM-like, fast but volatile

Memory is accessed via bit-addressed fields encoded in spiral format.

---

## 4. Register-Based Computation (Optional Layer)

Advanced hamsters can use registers for temporary computation:

- ALU operations on binary sequences
- Conditional branching simulated via indirect memory checks
- Future plans may include: ADD, XOR, SHIFT encoded in higher spiral layers

---

## 5. Code Simulation (C++ Example)

Below is a simplified VM loop example (full code in `vm.cpp`):

```cpp
// Pseudocode
READ 0001 0      → [LOAD addr 0001]
WRITE 0010 1011 0 → [STORE 1011 at 0010]
EMIT 1011 0      → [Output value]
CONTINUE 0       → [Do not emit yet]
STOP 0           → [End of program]
