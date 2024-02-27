# -*- coding: utf-8 -*-
g_description = """
A binary text tool (remake) for text exporting, importing and checking
    v0.6, developed by devseed
"""

import codecs
import logging
import argparse
from io import StringIO, BytesIO
from typing import Callable, Tuple, Union, List, Dict

try:
    from libutil import loadfiles, readlines, ftext_t, tbl_t, jtable_t, msg_t, save_ftext, load_ftext, load_tbl
except ImportError:
    exec("from libutil_v600 import loadfiles, readlines, ftext_t, tbl_t, jtable_t, msg_t, save_ftext, load_ftext, load_tbl")

__version__  = 600

# text basic functions
def iscjk(c: str): 
    if not hasattr(iscjk, 'ranges'):
        iscjk.ranges = [
            range(ord(u"\u2000"), ord(u"\u206f") + 1), # general punctuation
            range(ord(u"\u3000"), ord(u"\u303f") + 1), # cjk symbols and punctuation
            range(ord(u'\u3040'), ord(u'\u309f') + 1), # jp hiragana
            range(ord(u"\u30a0"), ord(u"\u30ff") + 1), # jp katakana
            range(ord(u"\u4e00"), ord(u"\u9fff") + 1), # cjk unified ideographs

            range(ord(u"\u2e80"), ord(u"\u2eff") + 1), # cjk radicals (中日韩汉字部首补充), 
            range(ord(u"\u3300"), ord(u"\u33ff") + 1), # cjk compatibility (中日韩兼容字符), ㌀
            range(ord(u"\u3400"), ord(u"\u4dbf") + 1), # cjk unified Ideographs Extension (中日韩统一表意文字扩展区), 㐀
            range(ord(u"\uf900"), ord(u"\ufaff") + 1), # cjk compatibility ideographs(中日韩兼容表意文字), 豈
            range(ord(u"\ufe30"), ord(u"\ufe4f") + 1), # cjk compatibility forms (中日韩兼容形式), ︰
            range(ord(u"\uff00"), ord(u"\uffef") + 1), # halfwidth and fullwidth Forms (半角及全角字符), ！	
        ]
    return any(ord(c) in r for r in iscjk.ranges)

def hascjk(s: str) -> bool:
    return any(iscjk(c) for c in s)

def istext(data: bytes, encoding="utf-8") -> bool:
    try: str(data, encoding)
    except UnicodeDecodeError: return False
    else: return True

def padding(n, bytes_padding: bytes) -> bytes:
    l1 = n //len(bytes_padding)
    l2 = n % len(bytes_padding)
    return l1*bytes_padding + bytes_padding[:l2]

def find_tbl(v: Union[str, bytes], tbl: List[tbl_t]):
    if not hasattr(find_tbl, "tbl") or find_tbl.tbl != tbl:
        find_tbl.tbl = tbl
        find_tbl.tcodemap = dict((t.tcode, i) for i, t in enumerate(tbl))
        find_tbl.tcharmap = dict((t.tchar, i) for i, t in enumerate(tbl))

    tcodemap, tcharmap = find_tbl.tcodemap, find_tbl.tcharmap
    if type(v) == str: return v in tcharmap
    elif type(v) == bytes: return v in tcodemap
    else: return None

def encode_tbl(text: str, tbl: List[tbl_t], bytes_fallback: bytes=None) -> bytes:
    """
    encoding the text by tbl
    :param tbl: for example [(tcode, tchar),...]
    :param fallback_bytes: encode these bytes when failed 
    :return: the encoded bytes
    """

    if not hasattr(encode_tbl, "tbl") or encode_tbl.tbl != tbl:
        encode_tbl.tbl = tbl
        encode_tbl.tblmap = dict((t.tchar, t.tcode) for t in tbl)

    data = BytesIO()
    tblmap = encode_tbl.tblmap
    for i, c in enumerate(text):
        if c in tblmap: data.write(tblmap[c])
        elif bytes_fallback: data.write(bytes_fallback)
        else:
            logging.error(f"failed with {c} at {i}, text='{text}'")
            return None
    
    return data.getvalue()

def decode_tbl(data: bytes, tbl: List[tbl_t]) -> str:
    """
    decoding the data by tbl
    :return: the decoded text in python string
    """

    if not hasattr(decode_tbl, "tbl") or decode_tbl.tbl != tbl:
        decode_tbl.tbl = tbl
        decode_tbl.tblrmap = dict((t.tcode, t.tchar) for t in tbl)
        decode_tbl.maxlen = max(len(t.tcode) for t in tbl)

    i = 0
    text = StringIO()
    tblrmap = decode_tbl.tblrmap
    maxlen = decode_tbl.maxlen
    while i < len(data):
        flag = False
        for j in range(1, maxlen+1):
            if data[i: i+j] not in tblrmap: continue
            text.write(tblrmap[data[i:i+j]])
            flag = True
            break
        if not flag:
            logging.error(f"[decode_tbl] failed with at {i}, data={data.hex(' ')}")
            return None
        i += j
    
    return text.getvalue()

def encode_general(text: str, enc: Union[str, List[tbl_t]]='utf-8', enc_error: Union[str, bytes]='ignore'):
    """
    automaticly judge to encode by tbl or encoding
    :param enc: tbl or encoding
    :param enc_error: errors or bytes_fallback
    """

    if type(enc)==str: 
        try: 
            return text.encode(enc, enc_error)
        except UnicodeEncodeError as e:
            logging.error(f"failed {e}, text='{text}'")
            return None
    else: return encode_tbl(text, enc, enc_error)

def split_extend(text, text_noeval=False) -> List[Union[slice, bytes]]:    
    start = 0
    res = []
    if not text_noeval:
        while start + 2 < len(text):
            end = text.find('{{', start)
            if end < 0: break
            res.append(slice(start, end))
            start = end + 2
            end = text.find('}}', start)
            if end < 0: raise ValueError(f"[split_extend] pattern not closed, text='{text}'")
            res.append(eval(text[start:end], {'__builtins__': None}))
            start = end + 2
    res.append(slice(start, None))
    return res

def encode_extend(text: str, enc: Union[str, List[tbl_t]]='utf-8', 
        enc_error: Union[str, bytes]="ignore", text_noeval=False) -> bytes:
    """
    general encoding method for ftext
    try replace [\n] [\r] in text
    extend {{expr}} to generate encbytes
    """

    text = text.replace(r'[\n]', '\n').replace(r'[\r]', '\r')
    res = bytearray()
    for t in split_extend(text, text_noeval):
        if type(t) == slice: 
            encbytes = encode_general(text[t], enc, enc_error)
            if encbytes is None: raise ValueError(f"encode_extend encode failed, {text[t]}")
            res += encbytes
        elif type(t) == bytes: res += t
    return res

# text functions
def detect_text_sjis(data, min_len=2) -> Tuple[List[int], List[int]]:
    i = 0
    start = -1
    n = len(data)
    addrs, sizes = [], []
    while i < n:
        flag_find = False
        c1 = data[i]
        if (c1 >= 0x20 and c1 <= 0x7f) or (c1 >= 0xa1 and c1 <= 0xdf):
            if start == -1: start = i # asci or half-katagana
            flag_find = True
            i += 1
        elif (c1 >= 0x81 and c1 <= 0x9f) or (c1 >= 0xe0 and c1 <= 0xef): 
            if i+2 > n: break
            c2 = data[i+1]
            if (c2 >= 0x40 and c2 <= 0x7e) or (c2 >= 0x80 and c2 <= 0xfc): 
                if start == -1: start = i # sjis
                flag_find = True
                i += 2
                
        if flag_find is False or i >= n:
            if start != -1:
                if i - start >= min_len:
                    addrs.append(start)
                    sizes.append(min(i-start, n))
                start = -1
            i += 1

    return addrs, sizes

def detect_text_multichar(data, encoding, min_len=2) -> Tuple[List[int], List[int]]:
    i = 0
    start = -1 
    n = len(data)
    addrs, sizes = [], []
    while i< len(data):
        flag_find = False
        c1 = data[i]
        if c1 >= 0x20 and c1 <= 0x7f:
            if start == -1:  start = i
            flag_find = True
            i += 1
        elif c1 > 0x7f:
            c = data[i: i+2]
            if istext(c, encoding=encoding):
                if start == -1: start = i
                flag_find = True
                i += 2

        if flag_find is False or i >= n:
            if start != -1:
                if i - start >= min_len:
                    addrs.append(start)
                    sizes.append(min(i-start, n))
                start = -1
            i += 1

    return addrs, sizes

def detect_text_tbl(data, tbl: List[tbl_t], min_len=2) -> Tuple[List[int], List[int]]: 
    """
    :param tbl: the customized charcode mapping to encoding charcode
    :return: addrs, sizes
    """
    i = 0
    start = -1 
    n = len(data)
    addrs, sizes = [], []
    lead_max = max(len(t.tcode)for t in tbl)
    while i < n:
        flag_find = False
        for j in range(1, lead_max + 1):
            if i + j > n: break
            if find_tbl(bytes(data[i: i+j]), tbl):
                if start==-1: start=i
                flag_find = True
                i += j
                break

        if flag_find is False or i >= n:
            if start != -1:
                if i-start >= min_len:
                    addrs.append(start)
                    sizes.append(min(i, n) - start)
                start = -1
            i += 1
        
    return addrs, sizes

def detect_text_utf8 (data, min_len=3) -> Tuple[List[int], List[int]]:
    if not hasattr(detect_text_utf8, "leadbyte_n"):
        detect_text_utf8.leadbyte_n = \
            [1 + (i >= 0xe0) + (i >= 0xf0) \
                if 0xbf < i < 0xf5 else 0 for i in range(256)]
    
    i = 0
    start = -1
    n = len(data)
    addrs, sizes = [], []
    leadbyte_n = detect_text_utf8.leadbyte_n
    while i < n:
        flag_find = False
        lead = data[i]
        j = leadbyte_n[lead]
        if j <= 0: # not seem as utf8
            if lead >= 0x20 and lead <= 0x7f:
                if start == -1: start = i
                i += 1
                flag_find = True
        else:  # seem as utf8
            if istext(data[i: i+j+1], 'utf-8'):
                if start == -1: start = i
                i += j + 1
                flag_find = True
        
        if flag_find is False or i >= n:
            if start != -1:
                if i - start >= min_len:
                    addrs.append(start)
                    sizes.append(min(i-start, n))
                start = -1
            i += 1
    
    return addrs, sizes

@loadfiles(0)
def extract_ftexts(binobj: Union[str, bytes], outpath=None, 
        encoding='utf-8', tblobj: Union[str, List[tbl_t]]=None, *, 
        min_len=2, has_cjk=True, data_slice=None) -> List[ftext_t]:
    """
    extract ftexts by search encoding or tbl in binfile
    """

    def _detect_text(target):
        if tbl is not None:
            logging.info("try detect_text_tbl")
            addrs, sizes = detect_text_tbl(target, tbl, min_len=min_len)
        elif encoding =="utf-8" :
            logging.info("try detect_text_utf8")
            addrs, sizes = detect_text_utf8(target, min_len=min_len)
        elif encoding == "sjis":
            logging.info("try detect_text_sjis")
            addrs, sizes = detect_text_sjis(target, min_len=min_len)
        else: 
            logging.info("try detect_text_multichar")
            addrs, sizes = detect_text_multichar(target,  encoding=encoding, min_len=min_len)
        return addrs, sizes

    def _make_ftexts(addrs, sizes):
        ftexts: List[ftext_t] = []
        for i, (addr, size) in enumerate(zip(addrs, sizes)):
            if tbl is None: text = str(data[addr: addr+size], encoding)
            else: text = decode_tbl(data[addr: addr+size], tbl)
            if has_cjk and not hascjk(text): continue
            text = text.replace('\n', r'[\n]').replace('\r', r'[\r]')
            ftexts.append(ftext_t(addr, size, text))
            logging.info(f"extract i={i} addr=0x{addr:x} size=0x{size:x} text='{text}'")
        return ftexts

    data = memoryview(binobj)
    data_slice = slice(0, None, 1) if data_slice is None else data_slice
    tbl =  load_tbl(tblobj, encoding=encoding) if tblobj else None
    addrs, sizes = _detect_text(data[data_slice])
    addrs = list(map(lambda x: x + data_slice.start, addrs))
    ftexts = _make_ftexts(addrs, sizes)
    if outpath: save_ftext(ftexts, ftexts, outpath)
    logging.info(f"finished, extract {len(ftexts)} ftexts")
    return ftexts

@loadfiles([0, 1, "referobj"])
def insert_ftexts(binobj: Union[str, bytes], 
        ftextsobj: Union[str, Tuple[List[ftext_t], List[ftext_t]]], 
        outpath=None, encoding='utf-8', tblobj: Union[str, List[tbl_t]]=None, *, 
        text_noeval=False, text_replace: Dict[bytes, bytes]=None,
        bytes_padding: bytes=b'\x00', bytes_fallback: bytes = None, 
        insert_longer=False, insert_shorter=False, insert_align=1, 
        referobj: Union[str, bytes]=None, jump_table: List[jtable_t] = None,
        f_before: Callable[[bytes, ftext_t], str] = None, 
        f_after: Callable[[bytes, memoryview, bytes, ftext_t], bytes] = None, 
    ) -> bytes:
    """
    :param ftextobj: ftextpath or (ftexts1, ftexts2)
    :param text_replace: replace text after f_before
    :param bytes_padding: padding the replace_bytes if not data_shorter
    :param bytes_fallback: bytes when encoding tbl failed
    :paran referobj: search from the reference obj to get new addr
    :param f_before: f(srcdata, ftext_t) -> replace_text
    :param f_after: f(srcdata, dstdata, encbytes, ftext_t) -> replace_bytes
    """
    
    def addr_find(t:ftext_t, data: bytes, refdata: bytes, addr_cache: set=None) -> int:
        addr = 0
        n = len(refdata)
        if t.addr + t.size > n: 
            logging.warning(f"0x{t.addr:x} + 0x{t.size:x} > 0x{n:x}")
            t.size = 0
            return -1
        target = refdata[t.addr: t.addr+t.size]
        while True:
            flag_find = False
            addr = data.find(target, addr)
            if addr >= 0:
                if addr_cache:
                    if addr in addr_cache:
                        # logging.debug(f"{t.addr: x} is in cache")
                        addr += 1
                        continue
                    else: flag_find = True
                else: flag_find = True
                
                if flag_find:
                    # logging.debug(f"0x{t.addr:x}->0x{addr:x}")
                    addr_cache |= {addr}
                    return addr
            else: 
                logging.warning(f"not find, addr=0x{t.addr:x} text='{t.text}'")
                return -1

    def insert_adjust(encbytes: bytes, t: ftext_t, *,
            insert_longer=False, insert_shorter=False, insert_align=1, bytes_padding=b'\x00'):
        # adjust encbytes size
        if len(encbytes) <= t.size:
            if not insert_shorter: 
                encbytes += padding(t.size - len(encbytes), bytes_padding)
        else:
            if not insert_longer: 
                logging.warning(f"strip longer text, addr={t.addr:x} size=0x{len(encbytes):x}>0x{t.size:x}")
                encbytes = encbytes[:t.size]
        
        # adjust encbytes align
        d = len(encbytes) - t.size
        if d % insert_align:
            if d > 0: encbytes += padding(insert_align - d%insert_align, bytes_padding)
            else: encbytes += padding(d%insert_align, bytes_padding)
        return encbytes
    
    refcache = set()
    refdata = memoryview(referobj) if referobj else None
    tbl = load_tbl(tblobj) if tblobj else None
    enc = tbl if tbl else encoding
    enc_error = bytes_fallback if tbl else ("ignore" if bytes_fallback else "strict")
    text_replace = text_replace if text_replace else dict()
    _, ftexts = load_ftext(readlines(ftextsobj)) if type(ftextsobj)==bytes else ftextsobj
    ftexts.sort(key=lambda x: x.addr)
    logging.info(f"load {len(ftexts)} ftexts")

    shift = 0
    last_addr = 0
    srcdata = bytes(binobj)
    dstio = BytesIO(srcdata)
    for i, t in enumerate(ftexts):
        addr = addr_find(t, srcdata, refdata, refcache) if refdata else t.addr
        if addr < 0: 
            logging.warning(f"ftext addr not find, i={i} addr=0x{t.addr:x} text='{t.text}'")
            continue
        dstio.write(srcdata[last_addr: addr])
        text = f_before(srcdata, t) if f_before else t.text
        for k, v in text_replace.items(): text = text.replace(k, v)
        encbytes = encode_extend(text, enc, enc_error, text_noeval)
        encbytes = insert_adjust(encbytes, t, insert_longer=insert_longer, 
            insert_shorter=insert_shorter, insert_align=insert_align, bytes_padding=bytes_padding)
        if f_after: 
            dstdata = dstio.getbuffer()[:dstio.tell()]
            encbytes = f_after(srcdata, dstdata, encbytes, t)
            dstio.flush()
            del dstdata
        dstio.write(encbytes)
        last_addr = addr + t.size
        shift += len(encbytes) - t.size
    
        if jump_table:
            for t in jump_table:
                if t.addr >= addr: t.addr_new  = t.addr + shift
                if t.toaddr >= addr:  t.toaddr_new = t.toaddr + shift
        _sizestr = f"0x{t.size:x}" + (f"->0x{len(encbytes):x}" if len(encbytes)!=t.size else "")
        logging.info(f"insert addr=0x{addr:x} size={_sizestr} text='{text}'")

    dstio.write(srcdata[last_addr:])
    if outpath: 
        with open(outpath, 'wb') as fp: fp.write(dstio.getbuffer()[:dstio.tell()] )
    logging.info(f"finished, datasize=0x{len(srcdata):x}->0x{dstio.tell():x}")
    return dstio.getbuffer()[:dstio.tell()] 

@loadfiles([0, "referobj"])
def check_ftexts(ftextsobj: Union[str, Tuple[List[ftext_t], List[ftext_t]]], outpath=None, 
        encoding='utf-8', tblobj: Union[str, List[tbl_t]]=None, *, 
        text_noeval=False, text_replace: Dict[bytes, bytes]=None,
        bytes_fallback: bytes = None, insert_longer=False, 
        referobj: Union[str, bytes]=None) -> List[msg_t]:
    """
    check the ftexts including format and charactors
    """
    
    msgs: List[msg_t] = []
    tbl = load_tbl(tblobj) if tblobj else None
    enc = tbl if tbl else encoding
    enc_error = bytes_fallback if tbl else ("ignore" if bytes_fallback else "strict")
    refdata = memoryview(referobj) if referobj else None
    text_replace = text_replace if text_replace else dict()
    ftexts1, ftexts2 = load_ftext(readlines(ftextsobj)) if type(ftextsobj)==bytes else ftextsobj
    if len(ftexts1) != len(ftexts2):
        msg = msg_t(0, f"○● count not match, {len(ftexts1)}!={len(ftexts2)}", logging.WARNING)
        logging.warning(msg.msg)
        msgs.append(msg)
    
    for i, (t1, t2) in enumerate(zip(ftexts1, ftexts2)):
        # check match
        if t1.addr != t2.addr:
            msg = msg_t(t1.addr, f"○●{i} addr not match, 0x{t1.addr:x}!=0x{t2.addr:x}", logging.WARNING)
            logging.warning(f"addr=0x{msg.id:x} {msg.msg}")
            msgs.append(msg)
        if t1.size != t2.size: 
            msg = msg_t(t1.addr, f"○●{i} size not match, 0x{t1.size:x}!=0x{t2.size:x}", logging.WARNING)
            logging.warning(f"addr=0x{msg.id:x} {msg.msg}")
            msgs.append(msg)
        
        # check src data
        if refdata:
            encbytes = encode_extend(t1.text, enc, enc_error, text_noeval)
            if encbytes != refdata[t1.addr: t1.addr + t1.size]:
                msg = msg_t(t1.addr, f"○{i} text not match, {t1.text}", logging.WARNING)
                logging.warning(f"addr=0x{msg.id:x} {msg.msg}")
                msgs.append(msg)

        # check dst data
        reject = set()
        text = t2.text
        for k, v in text_replace.items(): text = text.replace(k, v)
        for t in split_extend(text, text_noeval):
            if type(t) != slice: continue
            for j, c in enumerate(text[t]):
                x = encode_general(c, enc, enc_error)
                if x is None: reject |= {c}
        if len(reject): 
            reject_str = " ".join(list(reject))
            msg = msg_t(t1.addr, f"●{i} encode failed, reject=({reject_str}), text='{text}'", logging.ERROR)
            logging.error(f"addr=0x{msg.id:x} {msg.msg}")
            msgs.append(msg)

        encbytes = encode_general(text, enc, enc_error)
        if not insert_longer and encbytes and len(encbytes) > t1.size:
            msg = msg_t(t1.addr, f"●{i} size owerflow, 0x{len(encbytes):x}>0x{t2.size:x}", logging.WARNING)
            logging.error(f"addr=0x{msg.id:x}, {msg.msg}")
            msgs.append(msg)

    if outpath:
        with codecs.open(outpath, "w", "utf-8") as fp:
            fp.writelines(f"{logging.getLevelName(t.type)}:{t.id: x}: {t.msg}\n" for t in msgs)

    return msgs

def cli(cmdstr=None):
    def cmd_extract(args):
        logging.debug(repr(args))
        outpath = args.outpath if args.outpath!="" else None
        start = int(args.skip, 0) if args.skip else 0 
        end =  start + int(args.size, 0) if args.size else None
        extract_ftexts(args.binpath, outpath, 
            encoding=args.encoding, tblobj=args.tbl, 
            min_len=args.min_len, has_cjk=args.has_cjk, 
            data_slice=slice(start, end, 1))

    def cmd_insert(args):
        logging.debug(repr(args))
        outpath = args.outpath if args.outpath!="" else None
        text_replace = dict((t[0], t[1]) for t in  args.text_replace) if args.text_replace else None
        bytes_padding = bytes.fromhex(args.bytes_padding)
        bytes_fallback = bytes.fromhex(args.bytes_fallback) if args.bytes_fallback else None
        insert_ftexts(args.binpath, args.ftextpath, outpath, 
            encoding=args.encoding, tblobj=args.tbl, referobj=args.referpath, 
            text_noeval=args.text_noeval, text_replace=text_replace, 
            bytes_padding=bytes_padding, bytes_fallback=bytes_fallback, 
            insert_longer=args.insert_longer, insert_shorter=args.insert_shorter, 
            insert_align=args.insert_align)

    def cmd_check(args):
        logging.debug(repr(args))
        outpath = args.outpath if args.outpath!="" else None
        text_replace = dict((t[0], t[1]) for t in  args.text_replace) if args.text_replace else None
        bytes_fallback = bytes.fromhex(args.bytes_fallback) if args.bytes_fallback else None
        check_ftexts(args.ftextpath, outpath,  
            encoding=args.encoding, tblobj=args.tbl, referobj=args.referpath, 
            text_replace=text_replace, text_noeval=args.text_noeval,
            bytes_fallback=bytes_fallback, insert_longer=args.insert_longer)

    parser = argparse.ArgumentParser(description=g_description)
    subparsers = parser.add_subparsers(title="sub command")
    parser_e = subparsers.add_parser("extract", help="extract text in binfile to ftext")
    parser_i = subparsers.add_parser("insert", help="insert ftext to binfile")
    parser_c = subparsers.add_parser("check", help="check the ftext with binfile")

    for p in [parser_e, parser_i, parser_c]:
        p.add_argument("-o", "--outpath", default="out")
        p.add_argument("-e", "--encoding", default="utf-8", help="binfile encoding")
        p.add_argument("-t", "--tbl", default=None, help="binfile tbl")
        p.add_argument("--log_level", default="info", help="set log level", 
            choices=("none", "critical", "error", "warnning", "info", "debug"))
    parser_e.set_defaults(handler=cmd_extract)
    parser_e.add_argument("binpath")
    parser_e.add_argument('--has_cjk', action='store_true', help="filter non cjk text")
    parser_e.add_argument('--min_len', type=int, default=2, help="filter text below len")
    parser_e.add_argument('--skip', default=None, help="skip bytes to extract")
    parser_e.add_argument('--size', default=None, help="extract bytes size")
    parser_i.set_defaults(handler=cmd_insert)
    parser_i.add_argument("binpath")
    parser_i.add_argument("ftextpath")
    parser_i.add_argument("--refer", dest="referpath", help="use this referfile for calcuate addr")
    parser_i.add_argument("--text_noeval", action="store_true",  help="disable eval like {{b'\x00'}}")
    parser_i.add_argument("--text_replace", type=str, default=None, 
        metavar=('src', 'dst'), nargs=2, action='append', help="replace bytes after encoding ")
    parser_i.add_argument("--bytes_padding", type=str, default="00",  help="padding bytes (fromhex format)")
    parser_i.add_argument("--bytes_fallback", type=str, default=None, help="bytes after tbl failed")
    parser_i.add_argument("--insert_shorter", action="store_true", help="insert data can longer than origin")
    parser_i.add_argument("--insert_longer", action="store_true",  help="insert data can shorter than origin")
    parser_i.add_argument("--insert_align", default=1, help="insert data by align value")
    parser_c.set_defaults(handler=cmd_check)
    parser_c.add_argument("ftextpath")
    parser_c.add_argument("--refer", dest="referpath", help="binfile path")
    parser_c.add_argument("--text_noeval", action="store_true",  help="disable eval like {{b'\x00'}}")
    parser_c.add_argument("-r", "--text_replace", type=str, default=None, 
        metavar=('src', 'dst'), nargs=2, action='append', help="replace bytes after encoding ")
    parser_c.add_argument("--bytes_fallback", type=str, default=None, help="bytes after tbl failed")
    parser_c.add_argument("--insert_longer", action="store_true", help="insert data can shorter than origin")

    args = parser.parse_args(cmdstr.split(' ') if cmdstr else None)
    loglevel = args.log_level if hasattr(args, "log_level") else "info"
    logging.basicConfig(level=logging.getLevelName(loglevel.upper()), 
                        format="%(levelname)s:%(funcName)s: %(message)s")
    if hasattr(args, "handler"): args.handler(args)
    else: parser.print_help()

if __name__ == "__main__":
    cli()

"""
history:
v0.1, initial version with utf-8 support
... 
v0.6, remake to increase speed and simplify functions
"""