import random
from rsb import encode, decode

def stress_test(test_count):
    collision = False
    for _ in range(test_count):
        data = str(random.randint(0, 2**32))
        if decode(encode(data)) != data:
            collision = True
            break
    print("✅ 无碰撞" if not collision else "❌ 发现碰撞")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stress-test", type=int, default=1000)
    args = parser.parse_args()
    stress_test(args.stress_test)
