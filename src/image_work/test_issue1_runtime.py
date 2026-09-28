"""Regressions for the runtime paths reported in new-repository issue #1."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest
from PIL import Image, ImageFilter

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import tex_lib as TX
import hlh_codec as HLH
spec=importlib.util.spec_from_file_location("runtime",HERE/"79_runtime_labels.py")
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)
BASE=HERE.parent/"files"
PF=HERE.parent/"text_patch_work/patched_files"

class RuntimeTests(unittest.TestCase):
    def test_later_arc_stages_preserve_earlier_menu_patches(self):
        # These live outside 75/78's new targets and used to be overwritten.
        master=json.loads((PF.parent/"translation_master.json").read_text(encoding="utf-8"))
        groups=master["images"]["misc_full"]
        self.assertIn("Info/arc/bank111.arc",groups)
        for key in groups["Info/arc/bank111.arc"]:
            off=int(key,16);rel="Info/arc/bank111.arc"
            source=(BASE/rel).read_bytes();target=(PF/rel).read_bytes()
            hd=TX.parse_header(source,off);a=hd["img_off"];z=a+hd["imgsize"]
            self.assertNotEqual(source[a:z],target[a:z])
        # All three earlier bank113 menu stages must survive battle-start edits.
        sys.path.insert(0,str(PF.parent))
        from test_issue23_regressions import u8_file
        source=(BASE/"Info/arc/bank113.arc").read_bytes()
        target=(PF/"Info/arc/bank113.arc").read_bytes()
        for member in ("tex/bank113_tpl.ARC","scen/usel_mode.dat","scen/usel_gtitle.dat"):
            self.assertNotEqual(u8_file(source,member),u8_file(target,member),member)

    def test_actual_dol_unit_and_command_textures_are_replaced(self):
        original=(HERE.parent/"sys/main.dol").read_bytes()
        patched=(PF.parent/"patched_main.dol").read_bytes()
        self.assertEqual(len(original),len(patched))
        offsets=[o for o in TX.find_blocks(original) if 0x2065e0<=o<=0x243360]
        self.assertEqual(len(offsets),174)
        for off in offsets+list(R.COMMANDS)+list(R.TERRAINS):
            hd=TX.parse_header(original,off);a=hd["img_off"];z=a+hd["imgsize"]
            self.assertEqual(original[off:a],patched[off:a],hex(off))
            self.assertNotEqual(original[a:z],patched[a:z],hex(off))
            im=TX.decode(patched,off)
            self.assertIsNotNone(im)
            self.assertIsNotNone(im.getbbox())

    def test_character_plates_do_not_change_portraits_or_member_offsets(self):
        for i in range(16):
            rel=f"Info/tex/chr{i:02d}.arc"
            original=(BASE/rel).read_bytes();patched=(PF/rel).read_bytes()
            start,end=struct.unpack_from("<II",original)
            self.assertEqual(len(original),len(patched))
            self.assertEqual(original[:start],patched[:start])
            self.assertEqual(original[end:],patched[end:])
            before=HLH.decode_hlh(original[start:end]);after=HLH.decode_hlh(patched[start:end])
            self.assertEqual(before[:96],after[:96])
            self.assertNotEqual(before[96:],after[96:])
            self.assertIsNotNone(TX.decode(after,0).getbbox())

    def test_both_control_help_formats_keep_alpha_and_exterior_pixels(self):
        pairs=[]
        # Build a synthetic @Texture header for the standard TPL's C8 buffer.
        for root in (BASE,PF):
            b=(root/"Info/tpl/con_img.tpl").read_bytes()
            header=bytearray(64)
            for off,value in ((0x10,334),(0x14,182),(0x18,256),(0x38,61824)):
                struct.pack_into(">I",header,off,value)
            pairs.append(bytes(header)+b[0x20:0x220]+b[0x260:0x260+61824])
        resources=[tuple(pairs)]
        for rel in ("Effect/Arc/bank0.arc","Effect/Arc/bank1.arc","Effect/Arc/bank2.arc"):
            data=(BASE/rel).read_bytes();out=(PF/rel).read_bytes()
            off=next(o for o in TX.find_blocks(data) if
                     (TX.parse_header(data,o)["w"],TX.parse_header(data,o)["h"])==(334,182))
            hd=TX.parse_header(data,off);end=hd["img_off"]+hd["imgsize"]
            self.assertEqual(data[:hd["img_off"]],out[:hd["img_off"]])
            self.assertEqual(data[end:],out[end:])
            resources.append((data[off:end],out[off:end]))
        # The contour and all button/controller pixels outside label boxes
        # must survive the encode/decode round trip.
        boxes=[(39,4,102,27),(235,4,314,27),(255,51,334,80),
               (28,78,86,106),(70,129,155,156),(188,152,264,182),(248,113,323,142)]
        for a,b in resources:
            before=TX.decode(a,0);after=TX.decode(b,0)
            self.assertEqual(before.getchannel("A").tobytes(),after.getchannel("A").tobytes())
            for y in range(182):
                for x in range(334):
                    if not any(l<=x<r and t<=y<bt for l,t,r,bt in boxes):
                        self.assertEqual(before.getpixel((x,y)),after.getpixel((x,y)),(x,y))
            bg=Image.new("RGB",after.size,(25,35,40));bg.paste(after,(0,0),after)
            bg.resize((1002,546)).save(HERE/"out"/
                ("battle_help_verified.png" if a is resources[0][0] else "battle_help_effect_verified.png"))

    def test_help_title_and_mission3_punctuation(self):
        carrier=json.loads((PF.parent/"carrier_map.json").read_text(encoding="utf-8"))
        payload=b"".join(bytes.fromhex(carrier[c]) for c in "조작설명")
        data=(PF.parent/"patched_main.dol").read_bytes()
        for off in (0x2D3100,0x2D33DC):
            self.assertEqual(data[off:off+8],payload)
        master=json.loads((PF.parent/"translation_master.json").read_text(encoding="utf-8"))
        line=next(x["ko"] for x in master["dialogue"].values() if "건탱크 갑니다" in x["ko"])
        self.assertTrue(line.endswith("갑니다！"))
        self.assertNotIn("~",line)

if __name__=="__main__":
    unittest.main()
