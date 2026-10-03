#!/usr/bin/env python3
"""
generate_scratch.py
-------------------
Generates Gemini_AI.sb3 — a ready-to-import Scratch project that talks
to bot.py via two cloud variables using numeric text encoding.

Encoding scheme (identical in bot.py):
    KEY_CHARS[i] (0-indexed) → 2-digit code  str(i+1).zfill(2)
    encoded = "1" + concatenated codes
    Leading "1" is a sentinel so Scratch never drops a leading zero
    when it stores the value as a plain number.

UI: Conversation is shown in a scrollable CHAT list.
    Each Q is added as "You: <question>".
    Each A is word-wrapped into WRAP_WIDTH-char lines under a "Gemini:" header.
    A separator line is added between exchanges.

Usage:
    python generate_scratch.py
Output:
    Gemini_AI.sb3   <- import this into Scratch via File -> Load from your computer
"""

import hashlib
import io
import json
import zipfile

# ══════════════════════════════════════════════════════════════════
# KEY  (must be identical in bot.py)
# ══════════════════════════════════════════════════════════════════
KEY_CHARS = list(
    "abcdefghijklmnopqrstuvwxyz "   # codes 01-27
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"    # codes 28-53
    "0123456789"                     # codes 54-63
    ".,?!:;'\"()-/+=*@#%_&"         # codes 64-83
)
assert len(KEY_CHARS) == 83, f"KEY length mismatch: {len(KEY_CHARS)}"

# Cloud variable names (U+2601 = ☁)
CLOUD_IN  = "\u2601 INPUT"
CLOUD_OUT = "\u2601 OUTPUT"

WRAP_WIDTH = 35   # characters per wrapped line in the CHAT list

# ── Fixed variable / list IDs ─────────────────────────────────────
V_INPUT  = "vid_cloud_input"
V_OUTPUT = "vid_cloud_output"
V_ENC    = "vid_encoded"
V_DEC    = "vid_decoded"
V_I      = "vid_i"
V_J      = "vid_j"
V_N      = "vid_n"
V_CHAR   = "vid_char"
V_FOUND  = "vid_found"
V_CHUNK  = "vid_chunk"
L_KEY    = "lid_key"
L_CHAT   = "lid_chat"   # NEW: conversation history list


# ══════════════════════════════════════════════════════════════════
# Block Builder  (unchanged from v1)
# ══════════════════════════════════════════════════════════════════
class BB:
    """Lightweight Scratch 3 block-graph builder."""

    def __init__(self):
        self.blocks: dict = {}
        self._c = 0

    def _id(self) -> str:
        self._c += 1
        return f"b{self._c:05d}"

    def _mk(self, opcode, inputs=None, fields=None,
            toplevel=False, x=0, y=0) -> str:
        bid = self._id()
        d = {
            "opcode": opcode,
            "next": None,
            "parent": None,
            "inputs": inputs or {},
            "fields": fields or {},
            "shadow": False,
            "topLevel": toplevel,
        }
        if toplevel:
            d["x"] = x
            d["y"] = y
        self.blocks[bid] = d
        return bid

    # ── Chaining helpers ─────────────────────────────────────────
    def seq(self, *bids) -> str:
        for i in range(len(bids) - 1):
            a, b = bids[i], bids[i + 1]
            self.blocks[a]["next"] = b
            self.blocks[b]["parent"] = a
        return bids[0]

    def sub(self, ctrl: str, first: str, slot="SUBSTACK"):
        self.blocks[ctrl]["inputs"][slot] = [2, first]
        self.blocks[first]["parent"] = ctrl

    def par(self, child: str, parent: str):
        self.blocks[child]["parent"] = parent

    # ── Static input-value constructors ─────────────────────────
    @staticmethod
    def ls(v):  return [1, [10, str(v)]]
    @staticmethod
    def ln(v):  return [1, [4,  str(v)]]
    @staticmethod
    def ri(bid):   return [2, bid]
    @staticmethod
    def ris(bid):  return [3, bid, [10, ""]]
    @staticmethod
    def rin(bid):  return [3, bid, [4,  ""]]

    # ── Event ────────────────────────────────────────────────────
    def when_flag(self, x=10, y=10) -> str:
        return self._mk("event_whenflagclicked", toplevel=True, x=x, y=y)

    # ── Looks ────────────────────────────────────────────────────
    def say(self, msg) -> str:
        return self._mk("looks_say", {"MESSAGE": msg})

    # ── Sensing ──────────────────────────────────────────────────
    def ask(self, q) -> str:
        return self._mk("sensing_askandwait", {"QUESTION": q})

    def answer(self) -> str:
        return self._mk("sensing_answer")

    # ── Control ──────────────────────────────────────────────────
    def forever(self)           -> str: return self._mk("control_forever")
    def repeat(self, times)     -> str: return self._mk("control_repeat",    {"TIMES": times})
    def repeat_until(self, cond)-> str: return self._mk("control_repeat_until", {"CONDITION": cond})
    def wait_secs(self, secs)   -> str: return self._mk("control_wait",      {"DURATION": secs})
    def if_(self, cond)         -> str: return self._mk("control_if",        {"CONDITION": cond})
    def if_else(self, cond)     -> str: return self._mk("control_if_else",   {"CONDITION": cond})
    def wait_until(self, cond)  -> str: return self._mk("control_wait_until", {"CONDITION": cond})

    # ── Data – statements ────────────────────────────────────────
    def set_v(self, name, vid, val) -> str:
        return self._mk("data_setvariableto",
                        {"VALUE": val}, {"VARIABLE": [name, vid]})

    def chg_v(self, name, vid, amt) -> str:
        return self._mk("data_changevariableby",
                        {"VALUE": amt}, {"VARIABLE": [name, vid]})

    def del_list(self, lname, lid) -> str:
        return self._mk("data_deletealloflist", {}, {"LIST": [lname, lid]})

    def add_list(self, lname, lid, item) -> str:
        return self._mk("data_addtolist", {"ITEM": item}, {"LIST": [lname, lid]})

    # ── Data – reporters ─────────────────────────────────────────
    def v(self, name, vid) -> str:
        return self._mk("data_variable", {}, {"VARIABLE": [name, vid]})

    def item_of(self, lname, lid, idx) -> str:
        return self._mk("data_itemoflist", {"INDEX": idx}, {"LIST": [lname, lid]})

    def len_list(self, lname, lid) -> str:
        return self._mk("data_lengthoflist", {}, {"LIST": [lname, lid]})

    # ── Operators – reporters ────────────────────────────────────
    def join_(self, s1, s2)   -> str: return self._mk("operator_join",      {"STRING1": s1,   "STRING2": s2})
    def add_(self, a, b)      -> str: return self._mk("operator_add",       {"NUM1": a,       "NUM2": b})
    def sub_(self, a, b)      -> str: return self._mk("operator_subtract",  {"NUM1": a,       "NUM2": b})
    def div_(self, a, b)      -> str: return self._mk("operator_divide",    {"NUM1": a,       "NUM2": b})
    def eq_(self, a, b)       -> str: return self._mk("operator_equals",    {"OPERAND1": a,   "OPERAND2": b})
    def not_(self, op)        -> str: return self._mk("operator_not",       {"OPERAND": op})
    def lt_(self, a, b)       -> str: return self._mk("operator_lt",        {"OPERAND1": a,   "OPERAND2": b})
    def gt_(self, a, b)       -> str: return self._mk("operator_gt",        {"OPERAND1": a,   "OPERAND2": b})
    def or_(self, a, b)       -> str: return self._mk("operator_or",        {"OPERAND1": a,   "OPERAND2": b})
    def and_(self, a, b)      -> str: return self._mk("operator_and",       {"OPERAND1": a,   "OPERAND2": b})
    def len_str(self, s)      -> str: return self._mk("operator_length",    {"STRING": s})
    def letter_of(self, l, s) -> str: return self._mk("operator_letter_of", {"LETTER": l,     "STRING": s})


# ══════════════════════════════════════════════════════════════════
# Script Builder
# ══════════════════════════════════════════════════════════════════
def build_scripts(bb: BB) -> str:
    """
    Build all Scratch blocks.  Returns the when-flag block ID.

    Forever loop:
      1. ask → add "You: answer" to CHAT
      2. encode answer → set INPUT
      3. wait for OUTPUT
      4. decode OUTPUT → add "Gemini:" + wrapped lines to CHAT → add separator
      5. reset OUTPUT
    """

    # ── Top-level event ──────────────────────────────────────────
    flag = bb.when_flag(x=10, y=10)

    # ── KEY list setup ───────────────────────────────────────────
    del_key    = bb.del_list("KEY", L_KEY)
    add_blocks = [bb.add_list("KEY", L_KEY, BB.ls(ch)) for ch in KEY_CHARS]

    # ── Reset OUTPUT and clear CHAT ──────────────────────────────
    set_out_init  = bb.set_v(CLOUD_OUT, V_OUTPUT, BB.ln(0))
    del_chat_init = bb.del_list("CHAT", L_CHAT)

    # ── Forever ──────────────────────────────────────────────────
    forever_blk = bb.forever()

    bb.seq(flag, del_key, *add_blocks, set_out_init, del_chat_init, forever_blk)

    # ════ Inside FOREVER ════════════════════════════════════════

    # 1. Ask
    ask_blk = bb.ask(BB.ls("Ask Gemini:"))

    # 2. Add "You: <answer>" to CHAT
    ans_you  = bb.answer()
    join_you = bb.join_(BB.ls("You: "), BB.ris(ans_you)); bb.par(ans_you, join_you)
    add_you  = bb.add_list("CHAT", L_CHAT, BB.ris(join_you)); bb.par(join_you, add_you)

    # 3. Encode answer ────────────────────────────────────────────
    set_enc_mt = bb.set_v("encoded", V_ENC, BB.ls(""))
    set_i_1    = bb.set_v("i",       V_I,   BB.ln(1))

    # repeat (length of answer)
    ans0    = bb.answer()
    len_ans = bb.len_str(BB.ris(ans0));   bb.par(ans0,    len_ans)
    rpt_enc = bb.repeat(BB.rin(len_ans)); bb.par(len_ans, rpt_enc)

    # ── Inside rpt_enc ────────────────────────────────────────────
    i_r0    = bb.v("i", V_I)
    ans1    = bb.answer()
    let_blk = bb.letter_of(BB.rin(i_r0), BB.ris(ans1))
    bb.par(i_r0, let_blk); bb.par(ans1, let_blk)
    set_char    = bb.set_v("char", V_CHAR, BB.ris(let_blk)); bb.par(let_blk, set_char)
    set_found_0 = bb.set_v("found", V_FOUND, BB.ln(0))
    set_j_1     = bb.set_v("j",     V_J,     BB.ln(1))

    len_key0 = bb.len_list("KEY", L_KEY)
    rpt_key  = bb.repeat(BB.rin(len_key0)); bb.par(len_key0, rpt_key)

    # ── Inside rpt_key ────────────────────────────────────────────
    fnd0     = bb.v("found", V_FOUND)
    cnd_fnd0 = bb.eq_(BB.ris(fnd0), BB.ls("0")); bb.par(fnd0,     cnd_fnd0)
    if_fnd0  = bb.if_(BB.ri(cnd_fnd0));           bb.par(cnd_fnd0, if_fnd0)

    j0      = bb.v("j", V_J)
    itm0    = bb.item_of("KEY", L_KEY, BB.rin(j0)); bb.par(j0, itm0)
    chr0    = bb.v("char", V_CHAR)
    cnd_chr = bb.eq_(BB.ris(itm0), BB.ris(chr0)); bb.par(itm0, cnd_chr); bb.par(chr0, cnd_chr)
    if_chr  = bb.if_(BB.ri(cnd_chr));              bb.par(cnd_chr, if_chr)

    set_fnd1 = bb.set_v("found", V_FOUND, BB.ln(1))
    j1       = bb.v("j", V_J)
    cnd_lt10 = bb.lt_(BB.rin(j1), BB.ln(10)); bb.par(j1,      cnd_lt10)
    ife_lt10 = bb.if_else(BB.ri(cnd_lt10));    bb.par(cnd_lt10, ife_lt10)

    j2   = bb.v("j", V_J)
    jn0j = bb.join_(BB.ls("0"), BB.ris(j2));   bb.par(j2, jn0j)
    e0   = bb.v("encoded", V_ENC)
    jne0 = bb.join_(BB.ris(e0), BB.ris(jn0j)); bb.par(e0, jne0); bb.par(jn0j, jne0)
    set_enc_then = bb.set_v("encoded", V_ENC, BB.ris(jne0)); bb.par(jne0, set_enc_then)

    j3   = bb.v("j", V_J)
    e1   = bb.v("encoded", V_ENC)
    jne1 = bb.join_(BB.ris(e1), BB.ris(j3)); bb.par(e1, jne1); bb.par(j3, jne1)
    set_enc_else = bb.set_v("encoded", V_ENC, BB.ris(jne1)); bb.par(jne1, set_enc_else)

    bb.seq(set_fnd1, ife_lt10)
    bb.sub(if_chr,   set_fnd1)
    bb.sub(ife_lt10, set_enc_then, "SUBSTACK")
    bb.sub(ife_lt10, set_enc_else, "SUBSTACK2")
    bb.sub(if_fnd0, if_chr)
    chg_j = bb.chg_v("j", V_J, BB.ln(1))
    bb.seq(if_fnd0, chg_j)
    bb.sub(rpt_key, if_fnd0)

    chg_i = bb.chg_v("i", V_I, BB.ln(1))
    bb.seq(set_char, set_found_0, set_j_1, rpt_key, chg_i)
    bb.sub(rpt_enc, set_char)

    # set encoded = join("1", encoded)
    e2   = bb.v("encoded", V_ENC)
    jpfx = bb.join_(BB.ls("1"), BB.ris(e2)); bb.par(e2, jpfx)
    set_enc_pfx = bb.set_v("encoded", V_ENC, BB.ris(jpfx)); bb.par(jpfx, set_enc_pfx)

    # save previous OUTPUT so we strictly wait for a BRAND NEW response
    out_prev     = bb.v(CLOUD_OUT, V_OUTPUT)
    set_prev_out = bb.set_v("found", V_FOUND, BB.ris(out_prev)); bb.par(out_prev, set_prev_out)

    # set INPUT = encoded
    e3     = bb.v("encoded", V_ENC)
    set_in = bb.set_v(CLOUD_IN, V_INPUT, BB.ris(e3)); bb.par(e3, set_in)

    # say "Thinking..."
    say_think = bb.say(BB.ls("Thinking..."))

    # ── Wait with 15s timeout (30 x 0.5s) ─────────────────────────
    set_j_0  = bb.set_v("j", V_J, BB.ln(0))

    # Condition: (OUTPUT != 0) AND (OUTPUT != found)
    out0        = bb.v(CLOUD_OUT, V_OUTPUT)
    eq_zero     = bb.eq_(BB.ris(out0), BB.ln(0)); bb.par(out0, eq_zero)
    not_zero    = bb.not_(BB.ri(eq_zero));        bb.par(eq_zero, not_zero)

    out_cur     = bb.v(CLOUD_OUT, V_OUTPUT)
    old_out     = bb.v("found", V_FOUND)
    eq_old      = bb.eq_(BB.ris(out_cur), BB.ris(old_out)); bb.par(out_cur, eq_old); bb.par(old_out, eq_old)
    not_old     = bb.not_(BB.ri(eq_old));                  bb.par(eq_old, not_old)

    new_resp    = bb.and_(BB.ri(not_zero), BB.ri(not_old)); bb.par(not_zero, new_resp); bb.par(not_old, new_resp)

    j_val    = bb.v("j", V_J)
    gt_30    = bb.gt_(BB.rin(j_val), BB.ln(30)); bb.par(j_val, gt_30)
    or_cond  = bb.or_(BB.ri(new_resp), BB.ri(gt_30)); bb.par(new_resp, or_cond); bb.par(gt_30, or_cond)
    rpt_wait = bb.repeat_until(BB.ri(or_cond));  bb.par(or_cond, rpt_wait)

    wait_half = bb.wait_secs(BB.ln(0.5))
    chg_j_tim = bb.chg_v("j", V_J, BB.ln(1))
    bb.seq(wait_half, chg_j_tim)
    bb.sub(rpt_wait, wait_half)

    # 4. Decode OUTPUT (if not timed out) ─────────────────────────
    set_dec_mt = bb.set_v("decoded", V_DEC, BB.ls(""))
    set_n_2    = bb.set_v("n", V_N, BB.ln(2))

    out1    = bb.v(CLOUD_OUT, V_OUTPUT)
    len_out = bb.len_str(BB.ris(out1));           bb.par(out1,    len_out)
    sub1    = bb.sub_(BB.rin(len_out), BB.ln(1)); bb.par(len_out, sub1)
    div2    = bb.div_(BB.rin(sub1),    BB.ln(2)); bb.par(sub1,    div2)
    rpt_dec = bb.repeat(BB.rin(div2));             bb.par(div2,    rpt_dec)

    # ── Inside rpt_dec ────────────────────────────────────────────
    n0     = bb.v("n", V_N)
    np1    = bb.add_(BB.rin(n0), BB.ln(1)); bb.par(n0, np1)
    n1     = bb.v("n", V_N)
    out2   = bb.v(CLOUD_OUT, V_OUTPUT)
    let_n  = bb.letter_of(BB.rin(n1), BB.ris(out2)); bb.par(n1, let_n); bb.par(out2, let_n)
    out3   = bb.v(CLOUD_OUT, V_OUTPUT)
    let_n1 = bb.letter_of(BB.rin(np1), BB.ris(out3)); bb.par(np1, let_n1); bb.par(out3, let_n1)
    jchunk    = bb.join_(BB.ris(let_n), BB.ris(let_n1)); bb.par(let_n, jchunk); bb.par(let_n1, jchunk)
    set_chunk = bb.set_v("chunk", V_CHUNK, BB.ris(jchunk)); bb.par(jchunk, set_chunk)
    ck0     = bb.v("chunk", V_CHUNK)
    itm1    = bb.item_of("KEY", L_KEY, BB.ris(ck0)); bb.par(ck0, itm1)
    dc0     = bb.v("decoded", V_DEC)
    jdec    = bb.join_(BB.ris(dc0), BB.ris(itm1));   bb.par(dc0, jdec); bb.par(itm1, jdec)
    set_dec = bb.set_v("decoded", V_DEC, BB.ris(jdec)); bb.par(jdec, set_dec)
    chg_n   = bb.chg_v("n", V_N, BB.ln(2))
    bb.seq(set_chunk, set_dec, chg_n)
    bb.sub(rpt_dec, set_chunk)

    # 5. Add response to CHAT with word-wrap ──────────────────────
    add_verity = bb.add_list("CHAT", L_CHAT, BB.ls("Verity:"))

    # reuse n and chunk for the wrap loop
    set_n_wrap         = bb.set_v("n",     V_N,     BB.ln(1))
    set_chunk_empty    = bb.set_v("chunk", V_CHUNK, BB.ls(""))

    # repeat (length of decoded)
    dc_wlen   = bb.v("decoded", V_DEC)
    len_dec_w = bb.len_str(BB.ris(dc_wlen));    bb.par(dc_wlen,   len_dec_w)
    rpt_wrap  = bb.repeat(BB.rin(len_dec_w));   bb.par(len_dec_w, rpt_wrap)

    # ── Inside rpt_wrap ───────────────────────────────────────────
    ck_w  = bb.v("chunk", V_CHUNK)
    n_w   = bb.v("n",     V_N)
    dc_w  = bb.v("decoded", V_DEC)
    let_w = bb.letter_of(BB.rin(n_w), BB.ris(dc_w)); bb.par(n_w, let_w); bb.par(dc_w, let_w)
    jck_w = bb.join_(BB.ris(ck_w), BB.ris(let_w));   bb.par(ck_w, jck_w); bb.par(let_w, jck_w)
    set_ck_w = bb.set_v("chunk", V_CHUNK, BB.ris(jck_w)); bb.par(jck_w, set_ck_w)

    # if (length of chunk = WRAP_WIDTH)
    ck_w2    = bb.v("chunk", V_CHUNK)
    len_ck_w = bb.len_str(BB.ris(ck_w2));                   bb.par(ck_w2,    len_ck_w)
    cnd_wrap = bb.eq_(BB.rin(len_ck_w), BB.ln(WRAP_WIDTH)); bb.par(len_ck_w, cnd_wrap)
    if_wrap  = bb.if_(BB.ri(cnd_wrap));                      bb.par(cnd_wrap, if_wrap)

    # then: add chunk to CHAT, reset chunk
    ck_w3       = bb.v("chunk", V_CHUNK)
    add_ck_line = bb.add_list("CHAT", L_CHAT, BB.ris(ck_w3)); bb.par(ck_w3, add_ck_line)
    set_ck_mt   = bb.set_v("chunk", V_CHUNK, BB.ls(""))
    bb.seq(add_ck_line, set_ck_mt)
    bb.sub(if_wrap, add_ck_line)

    chg_n_w = bb.chg_v("n", V_N, BB.ln(1))
    bb.seq(set_ck_w, if_wrap, chg_n_w)
    bb.sub(rpt_wrap, set_ck_w)

    # After wrap loop: if chunk not empty, add remaining text
    ck_w4      = bb.v("chunk", V_CHUNK)
    cnd_mt     = bb.eq_(BB.ris(ck_w4), BB.ls("")); bb.par(ck_w4,    cnd_mt)
    not_mt     = bb.not_(BB.ri(cnd_mt));             bb.par(cnd_mt,   not_mt)
    if_not_mt  = bb.if_(BB.ri(not_mt));              bb.par(not_mt,   if_not_mt)
    ck_w5      = bb.v("chunk", V_CHUNK)
    add_remain = bb.add_list("CHAT", L_CHAT, BB.ris(ck_w5)); bb.par(ck_w5, add_remain)
    bb.sub(if_not_mt, add_remain)

    # Separator line
    add_sep = bb.add_list("CHAT", L_CHAT, BB.ls("------------------------------"))

    # Chain decode + display blocks
    bb.seq(
        set_dec_mt, set_n_2, rpt_dec,
        add_verity, set_n_wrap, set_chunk_empty, rpt_wrap, if_not_mt, add_sep
    )

    # ── If-Else block: check if timed out ─────────────────────────
    j_chk     = bb.v("j", V_J)
    gt_30_chk = bb.gt_(BB.rin(j_chk), BB.ln(30)); bb.par(j_chk, gt_30_chk)
    ife_tim   = bb.if_else(BB.ri(gt_30_chk));     bb.par(gt_30_chk, ife_tim)

    # Timed out branch (SUBSTACK):
    add_to_err = bb.add_list("CHAT", L_CHAT, BB.ls("Verity: [No response from cloud]"))
    add_sep_to = bb.add_list("CHAT", L_CHAT, BB.ls("------------------------------"))
    bb.seq(add_to_err, add_sep_to)
    bb.sub(ife_tim, add_to_err, "SUBSTACK")

    # Success branch (SUBSTACK2):
    bb.sub(ife_tim, set_dec_mt, "SUBSTACK2")

    # say "" to clear the "Thinking..." bubble
    clear_say = bb.say(BB.ls(""))

    # Reset OUTPUT for next question
    set_out_end = bb.set_v(CLOUD_OUT, V_OUTPUT, BB.ln(0))

    # ── Wire the full forever chain ───────────────────────────────
    bb.seq(
        ask_blk, add_you,
        set_enc_mt, set_i_1, rpt_enc,
        set_enc_pfx, set_prev_out, set_in, say_think,
        set_j_0, rpt_wait, ife_tim,
        clear_say, set_out_end
    )
    bb.sub(forever_blk, ask_blk)

    return flag


# ══════════════════════════════════════════════════════════════════
# Project JSON Builder
# ══════════════════════════════════════════════════════════════════
def build_project(bb: BB, backdrop_md5: str, sprite_md5: str) -> dict:
    return {
        "targets": [
            {
                "isStage": True,
                "name": "Stage",
                "variables": {
                    V_INPUT:  [CLOUD_IN,  0, True],
                    V_OUTPUT: [CLOUD_OUT, 0, True],
                },
                "lists": {},
                "broadcasts": {},
                "blocks": {},
                "comments": {},
                "currentCostume": 0,
                "costumes": [{
                    "name": "backdrop1",
                    "dataFormat": "svg",
                    "assetId": backdrop_md5,
                    "md5ext": f"{backdrop_md5}.svg",
                    "rotationCenterX": 240,
                    "rotationCenterY": 180,
                }],
                "sounds": [],
                "volume": 100,
                "layerOrder": 0,
                "tempo": 60,
                "videoTransparency": 50,
                "videoState": "on",
                "textToSpeechLanguage": None,
            },
            {
                "isStage": False,
                "name": "Gemini",
                "variables": {
                    V_ENC:   ["encoded", ""],
                    V_DEC:   ["decoded", ""],
                    V_I:     ["i",       0],
                    V_J:     ["j",       0],
                    V_N:     ["n",       0],
                    V_CHAR:  ["char",    ""],
                    V_FOUND: ["found",   0],
                    V_CHUNK: ["chunk",   ""],
                },
                "lists": {
                    L_KEY:  ["KEY",  []],
                    L_CHAT: ["CHAT", []],   # conversation history
                },
                "broadcasts": {},
                "blocks": bb.blocks,
                "comments": {},
                "currentCostume": 0,
                "costumes": [{
                    "name": "costume1",
                    "dataFormat": "svg",
                    "assetId": sprite_md5,
                    "md5ext": f"{sprite_md5}.svg",
                    "rotationCenterX": 48,
                    "rotationCenterY": 48,
                }],
                "sounds": [],
                "volume": 100,
                "layerOrder": 1,
                "visible": True,
                "x": 0,
                "y": 0,
                "size": 100,
                "direction": 90,
                "draggable": False,
                "rotationStyle": "all around",
            },
        ],
        "monitors": [],
        "extensions": [],
        "meta": {
            "semver": "3.0.0",
            "vm": "2.3.4",
            "agent": "scratch-gemini-ai-generator",
        },
    }


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════
def main():
    BACKDROP_SVG = (
        b'<svg version="1.1" xmlns="http://www.w3.org/2000/svg"'
        b' width="480" height="360">'
        b'<rect width="480" height="360" fill="#e8f4fd"/>'
        b'<text x="240" y="150" font-family="Arial,sans-serif" font-size="52"'
        b' font-weight="bold" text-anchor="middle" fill="#1a73e8">Gemini AI</text>'
        b'<text x="240" y="200" font-family="Arial,sans-serif" font-size="22"'
        b' text-anchor="middle" fill="#5f6368">on Scratch</text>'
        b'<text x="240" y="345" font-family="Arial,sans-serif" font-size="14"'
        b' text-anchor="middle" fill="#9aa0a6">Make sure bot.py is running!</text>'
        b'</svg>'
    )
    SPRITE_SVG = (
        b'<svg version="1.1" xmlns="http://www.w3.org/2000/svg"'
        b' width="96" height="96">'
        b'<circle cx="48" cy="48" r="44" fill="#1a73e8"/>'
        b'<text x="48" y="62" font-family="Arial,sans-serif" font-size="30"'
        b' font-weight="bold" text-anchor="middle" fill="white">AI</text>'
        b'</svg>'
    )

    backdrop_md5 = hashlib.md5(BACKDROP_SVG).hexdigest()
    sprite_md5   = hashlib.md5(SPRITE_SVG).hexdigest()

    bb = BB()
    build_scripts(bb)
    project = build_project(bb, backdrop_md5, sprite_md5)

    output_path = "Gemini_AI.sb3"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json",        json.dumps(project, ensure_ascii=False))
        zf.writestr(f"{backdrop_md5}.svg", BACKDROP_SVG)
        zf.writestr(f"{sprite_md5}.svg",   SPRITE_SVG)
    buf.seek(0)
    with open(output_path, "wb") as f:
        f.write(buf.read())

    print(f"[OK] Generated:     {output_path}")
    print(f"     Blocks created: {len(bb.blocks)}")
    print()
    print("CHAT list shows conversation history.")
    print(f"Responses are word-wrapped at {WRAP_WIDTH} chars per line.")


if __name__ == "__main__":
    main()
