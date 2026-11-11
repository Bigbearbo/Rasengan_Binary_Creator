#!/usr/bin/env python3
"""01AI 二層具名函式定義/呼叫實驗性驗證器（版本 v1）。

定義: 001|0000|0000|1100|NAME|OP1|OP2|1110
呼叫: 001|0000|0100|1100|NAME|DATA1|DATA2|1110
NAME 為5位末尾0的一層名稱詞；OP1/OP2 各4位。DATA1/DATA2 等長且尾0，依總長推導。
OP1 支援 v1 AND(1010)、OR(1100)，OP2 支援 NegEcho(0010)、CUT(1000)。
此為兩階段管線，不是完整的自由程式/函式虛擬機。
"""
from pathlib import Path
import importlib.util
import sys
src=Path(__file__).with_name('MLP_二層協議_編解碼驗證器.py')
spec=importlib.util.spec_from_file_location('mlp_codec_current',src)
codec=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=codec
spec.loader.exec_module(codec)
HEADER_DEF='001000000001100'
HEADER_CALL='001000001001100'
END='1110'


def parse_def(s: str):
    codec.bits(s,'definition')
    if not s.startswith(HEADER_DEF) or not s.endswith(END):
        raise ValueError('definition header/end invalid')
    payload=s[len(HEADER_DEF):-len(END)]
    if len(payload)!=13: raise ValueError('need 5-bit name and 4+4-bit program')
    name,op1,op2=payload[:5],payload[5:9],payload[9:]
    if not name.endswith('0'): raise ValueError('name word must end in 0')
    if op1 not in ('1010','1100') or op2 not in ('0010','1000'):
        raise ValueError('supported v1 pipelines: AND/OR -> NegEcho/CUT')
    return name,(op1,op2)


def parse_call(s: str,registry: dict):
    codec.bits(s,'call')
    if not s.startswith(HEADER_CALL) or not s.endswith(END):
        raise ValueError('call header/end invalid')
    payload=s[len(HEADER_CALL):-len(END)]
    if len(payload)<9 or (len(payload)-5)%2:
        raise ValueError('need 5-bit name and two equal-length operands')
    name=payload[:5]
    if name not in registry: raise ValueError('undefined name')
    n=(len(payload)-5)//2
    if n<2: raise ValueError('operands too short')
    a,b=payload[5:5+n],payload[5+n:]
    if not a.endswith('0') or not b.endswith('0'):
        raise ValueError('data must end in 0')
    op1,op2=registry[name]
    if op1 not in ('1010','1100') or op2 not in ('0010','1000'):
        raise ValueError('unsupported pipeline')
    intermediate=codec.calc('and' if op1=='1010' else 'or',[a,b])
    output=codec.calc('neg' if op2=='0010' else 'cut',[intermediate])
    return name,a,b,output


def encode_def(name,op1,op2):
    s=HEADER_DEF+name+op1+op2+END
    assert parse_def(s)==(name,(op1,op2))
    return s


def encode_call(name,a,b):
    return HEADER_CALL+name+a+b+END


def test():
    reg={}
    for name,prog in [('10100',('1010','0010')),('11100',('1010','0010')),
                      ('00100',('1010','1000')),('01100',('1100','1000')), ('10110',('1100','1000'))]:
        assert parse_def(encode_def(name,*prog))==(name,prog)
        reg[name]=prog
    expected=[
        ('00100','10101100','11010110','1000010'),
        ('01100','10101100','11010110','1111111'),
        ('00100','1111110','0101010','010101'),
        ('11100','0000000','0000000','1111110'),
        ('10110','1010100','0110010','111011'),
    ]
    for name,a,b,answer in expected:
        assert parse_call(encode_call(name,a,b),reg)==(name,a,b,answer)
    # The student may expand both operands while preserving the existing function definition.
    try: parse_call(encode_call('00100','10101100','11010110'),{})
    except ValueError:pass
    else:raise AssertionError('undefined name was accepted')
    for bad in [encode_call('00100','1010110','11010110'),encode_call('00100','10101101','11010110')]:
        try:parse_call(bad,reg)
        except ValueError:pass
        else:raise AssertionError('invalid word length/end accepted')
    print('PASS: named function 7/8 bit inputs, AND/OR -> NegEcho/CUT, student name 10110, invalid-input checks')


if __name__=='__main__':test()