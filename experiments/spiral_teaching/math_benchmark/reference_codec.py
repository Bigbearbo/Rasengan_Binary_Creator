#!/usr/bin/env python3
"""MLP 二層協議題目編碼、解析、求值與回覆核對。

現行受控教學語法（明示詞表，不把位元流任意猜成唯一切詞）：
  數學: 001 | 0000 | 1100 | OP | DATA [| DATA2] | END
  批改: 001 | 0100 | 1100 | FEEDBACK | 110
一層算符 n=3: 000 echo / 010 neg / 100 zero / 110 END
一層算符 n=4: 0000 echo / 0010 neg / 0100 zero / 0110 one /
                1000 cut / 1010 and / 1110 END
資料詞需以 0 結尾。原則是 OP/END 長度固定，單資料詞由剩餘長度決定；
雙資料詞 AND 需要雙方預設 n，預設每個資料 4 bits；不猜兩個不等長詞邊界。
版本宣告（獨立一行）：001|1000|0000|1100 → v0；001|1000|0100|1100 → v1。
v1 以 1100 表示 OR；v2 以同一 1100 表示 XOR；v0 不允許此碼。解析單題時必須顯式提供 --version v1 或 v2。
答案獨立成行，可能跟保留句號同碼；CUT 答案也未必以 0 結尾。
本程式不等於完整可演化的螺旋語解析器；僅針對這輪已明確共識的子集。
"""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass

HEADER_MATH = ('001','0000','1100')
HEADER_FEEDBACK = ('001','0100','1100')
HEADER_VERSION = ('001','1000')
VERSION_CODES = {'0000':'v0', '0100':'v1', '1000':'v2'}
OPS = {
    3: {'000': 'echo', '010': 'neg', '100': 'zero'},
    4: {'0000': 'echo', '0010': 'neg', '0100': 'zero', '0110': 'one', '1000': 'cut', '1010': 'and'},
}
ENDS = {3:'110',4:'1110'}
FEEDBACK = {'000':'incorrect','010':'correct'}

def known_ops(width:int,version:str='v0') -> dict:
    if version not in ('v0','v1','v2'):raise CodecError('未知版本')
    if width not in OPS:raise CodecError('未知詞階')
    op=OPS[width].copy()
    if version in ('v1','v2') and width==4:op['1100']='or' if version=='v1' else 'xor'
    return op

def encode_version(version:str) -> str:
    rev={v:k for k,v in VERSION_CODES.items()}
    if version not in rev:raise CodecError('未知版本')
    return ''.join(HEADER_VERSION)+rev[version]+'1100'

def decode_version(s:str) -> dict:
    bits(s,'版本宣告')
    if not s.startswith(''.join(HEADER_VERSION)) or len(s)!=15 or not s.endswith('1100'):
        raise CodecError('不符合二層版本宣告格式')
    code=s[7:11]
    if code not in VERSION_CODES:raise CodecError('未定義的版本詞')
    return {'kind':'version','code':code,'version':VERSION_CODES[code],
            'words':['001','1000',code,'1100']}

class CodecError(ValueError):
    pass


def bits(s: str, name: str) -> str:
    if not s or set(s) - {'0','1'}:
        raise CodecError(f'{name} 只能是非空 0/1 字串')
    return s


def word(s: str, name: str) -> str:
    bits(s,name)
    if not s.endswith('0'):
        raise CodecError(f'{name} 必須以 0 結尾')
    return s


def calc(op: str, data: list[str]) -> str:
    if op == 'echo': return data[0]
    if op == 'neg': return ''.join('1' if b=='0' else '0' for b in data[0][:-1])+'0'
    if op == 'zero': return '0'*len(data[0])
    if op == 'one': return '1'*(len(data[0])-1)+'0'
    if op == 'cut': return data[0][:-1]
    if op == 'and': return ''.join('1' if a=='1' and b=='1' else '0' for a,b in zip(data[0],data[1]))
    if op == 'or': return ''.join('1' if a=='1' or b=='1' else '0' for a,b in zip(data[0],data[1]))
    if op == 'xor': return ''.join('1' if (a=='1')!=(b=='1') else '0' for a,b in zip(data[0],data[1]))
    raise CodecError('未知算符')


def encode_math(op:str,data:list[str],width:int=4,version:str='v0') -> str:
    if width not in OPS: raise CodecError('只能使用三位或四位詞表')
    inverse={v:k for k,v in known_ops(width,version).items()}
    if op not in inverse:raise CodecError('算符不在當前詞表')
    if len(data)!=(2 if op in ('and','or','xor') else 1): raise CodecError('算符的資料詞數量不符')
    for i,d in enumerate(data): word(d,f'資料詞{i+1}')
    if op in ('and','or','xor') and len(data[0])!=len(data[1]):raise CodecError('雙運算元的資料詞長度須一致')
    return ''.join(HEADER_MATH)+inverse[op]+''.join(data)+ENDS[width]


def decode_math(s:str,width:int=4,and_bits:int=4,strict_data_bits:int|None=None,version:str='v0') -> dict:
    bits(s,'題目')
    if width not in OPS:raise CodecError('不能解析此算符寬度')
    prefix=''.join(HEADER_MATH)
    if not s.startswith(prefix): raise CodecError('不是本版本數學二層前綴 001|0000|1100')
    rem=s[len(prefix):]
    end=ENDS[width]
    if not rem.endswith(end): raise CodecError(f'缺少 {width} 位句號 {end}')
    rem=rem[:-width]
    if len(rem)<width:raise CodecError('缺少完整算符')
    op_bits, payload=rem[:width],rem[width:]
    v_ops=known_ops(width,version)
    if op_bits not in v_ops:raise CodecError(f'保留或未知算符：{op_bits}')
    op=v_ops[op_bits]
    if op in ('and','or','xor'):
        if and_bits<=0:raise CodecError('雙運算元資料位數需為正')
        if len(payload)!=2*and_bits:raise CodecError(f'AND 預期 2 個各 {and_bits} 位資料，卻收到 {len(payload)} 位')
        data=[payload[:and_bits],payload[and_bits:]]
    else:
        if strict_data_bits is not None and len(payload)!=strict_data_bits:
            raise CodecError(f'預期資料詞長 {strict_data_bits}，實際 {len(payload)}')
        data=[payload]
    for i,d in enumerate(data):word(d,f'資料詞{i+1}')
    answer=calc(op,data)
    return {'kind':'math','width':width,'prefix':list(HEADER_MATH),'op_code':op_bits,
            'operator':op,'data':data,'end':end,'answer':answer,
            'words':list(HEADER_MATH)+[op_bits]+data+[end]}


def decode_feedback(s:str)->dict:
    bits(s,'批改')
    prefix=''.join(HEADER_FEEDBACK)
    if not s.startswith(prefix) or not s.endswith('110'):
        raise CodecError('不是已教的二層批改格式')
    payload=s[len(prefix):-3]
    if len(payload)!=3 or not payload.endswith('0'):
        raise CodecError('批改詞須為三位一層詞')
    return {'kind':'feedback','code':payload,'status':FEEDBACK.get(payload,'undefined'),
            'words':list(HEADER_FEEDBACK)+[payload,'110']}


def pretty(d:dict)->str:
    phrase=' | '.join(d['words'])
    if d['kind']=='feedback':return f'{phrase}\n批改詞 {d["code"]}：{d["status"]}'
    if d['kind']=='version':return f'{phrase}\n版本：{d["version"]}'
    return f'{phrase}\n{d["operator"]}({", ".join(d["data"])}) = {d["answer"]}'


def tests() -> None:
    # Test all 4-bit data unary operators plus AND pairs on four-bit data.
    vals=[f'{i:03b}0' for i in range(8)]
    n=0
    for width in (3,4):
        for name in OPS[width].values():
            if name=='and':
                for x in vals:
                    for y in vals:
                        q=encode_math(name,[x,y],width)
                        v=decode_math(q,width)
                        assert v['answer']==calc(name,[x,y])
                        assert v['data']==[x,y]
                        n+=1
            else:
                for x in vals:
                    q=encode_math(name,[x],width)
                    v=decode_math(q,width)
                    assert v['answer']==calc(name,[x])
                    assert v['data']==[x]
                    n+=1
    # Current live transcript regressions: teacher previous question and student's repeat.
    assert decode_math('001000011001010111001101110',4)['answer']=='0110'
    assert decode_math('001000011001010110001001110',4)['answer']=='0100'
    assert decode_math('001000011001010110010101110',4)['answer']=='1000'
    assert decode_math('001000011001010110001101110',4)['answer']=='0100'
    assert decode_math('0010000110010001010101110',4)['answer']=='10101'
    assert decode_math('00100001100001000001110',4)['answer']=='1110'
    assert decode_math('001000011000100110110',3)['answer']=='1000'
    assert decode_feedback('00101001100000110')['status']=='incorrect'
    assert decode_feedback('00101001100010110')['status']=='correct'
    assert decode_feedback('00101001100100110')['status']=='undefined'
    for invalid in ['001000011001110101110', # reserved 4bit op
                    '001000011001010110001011110', # AND second data ends in 1
                    '00100001100101011000100110']: # four-bit END missing
        try: decode_math(invalid,4)
        except CodecError:pass
        else:raise AssertionError(f'無效題目未拒絕：{invalid}')
    assert decode_version(encode_version('v0'))['version']=='v0'
    assert decode_version(encode_version('v1'))['version']=='v1'
    for a,b,expected in [('1010100','0111000','1111100'),('1001000','0110010','1111010'),('0101100','1001010','1101110')]:
        q=encode_math('or',[a,b],version='v1')
        assert decode_math(q,and_bits=7,version='v1')['answer']==expected
        try:decode_math(q,and_bits=7,version='v0')
        except CodecError:pass
        else:raise AssertionError('v0 錯誤接受 v1 新算符')
    assert decode_version(encode_version('v2'))['version']=='v2'
    for a,b,ex_or,ex_xor in [('1010100','0111000','1111100','1101100'),('1110000','0110100','1110100','1000100'),('1101100','1010100','1111100','0111000')]:
        for ver,op,expected in [('v1','or',ex_or),('v2','xor',ex_xor)]:
            q=encode_math(op,[a,b],version=ver)
            assert decode_math(q,and_bits=7,version=ver)['answer']==expected
            assert decode_math(q,and_bits=7,version=ver)['operator']==op
        assert encode_math('or',[a,b],version='v1')==encode_math('xor',[a,b],version='v2')
    print(f'PASS: {n} 個生成/解析/求值往返測例，歷史回歸、v0/v1/v2 版本與 OR/XOR 同碼測試')


def main() -> None:
    ap=argparse.ArgumentParser(description='MLP 二層數學與批改詞編碼／解碼／驗證器')
    sub=ap.add_subparsers(dest='cmd',required=True)
    for cmd in ('parse','check'):
        p=sub.add_parser(cmd)
        p.add_argument('question')
        if cmd=='check':p.add_argument('answer')
        p.add_argument('--width',type=int,choices=(3,4),default=4)
        p.add_argument('--and-bits',type=int,default=4)
        p.add_argument('--data-bits',type=int)
        p.add_argument('--json',action='store_true')
        p.add_argument('--version',choices=('v0','v1','v2'),default='v0')
    gen=sub.add_parser('make')
    gen.add_argument('operation',choices=('echo','neg','zero','one','cut','and','or','xor'))
    gen.add_argument('data',nargs='+')
    gen.add_argument('--width',type=int,choices=(3,4),default=4)
    gen.add_argument('--version',choices=('v0','v1','v2'),default='v0')
    v=sub.add_parser('version');v.add_argument('name',choices=('v0','v1','v2'))
    sub.add_parser('test')
    p=sub.add_parser('feedback');p.add_argument('code',choices=('000','010'))
    args=ap.parse_args()
    try:
        if args.cmd=='test':tests();return
        if args.cmd=='version':print(encode_version(args.name));return
        if args.cmd=='feedback':
            q=''.join(HEADER_FEEDBACK)+args.code+'110'
            print(q);print(pretty(decode_feedback(q)));return
        if args.cmd=='make':
            q=encode_math(args.operation,args.data,args.width,args.version)
            print(q);print(pretty(decode_math(q,args.width,and_bits=len(args.data[0]),version=args.version)));return
        if args.cmd in ('parse','check'):
            if args.question.startswith(''.join(HEADER_VERSION)):
                if args.cmd=='check':raise CodecError('版本宣告無答案')
                result=decode_version(args.question)
            elif args.question.startswith(''.join(HEADER_FEEDBACK)):
                if args.cmd=='check':raise CodecError('批改語句無數學答案，請用 parse')
                result=decode_feedback(args.question)
            else:result=decode_math(args.question,args.width,args.and_bits,args.data_bits,args.version)
            if args.json:print(json.dumps(result,ensure_ascii=False,indent=2))
            else:print(pretty(result))
            if args.cmd=='check':
                bits(args.answer,'學生回答')
                passed=args.answer==result['answer']
                print('PASS' if passed else f'FAIL：學生回答 {args.answer}，正解 {result["answer"]}')
                if not passed:sys.exit(1)
    except CodecError as e:
        print(f'ERROR: {e}',file=sys.stderr)
        sys.exit(2)

if __name__=='__main__':main()