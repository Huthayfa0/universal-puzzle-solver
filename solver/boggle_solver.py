"""Boggle puzzle solver.

Rules:
- Find as many words as possible on the grid.
- Move from one letter (dice) to another if it is a neighbour (all 8 directions).
- Cannot use a letter (dice) more than once in a word.
- Points per word: 3–4 letters = 1, 5 = 2, 6 = 3, 7 = 5, 8+ = 11.
- Puzzle is solved when you collect 30% / 60% / 90% of total possible points
  for easy / hard / extreme.
"""

import os
from .solver import BaseSolver

# 8 directions: E, W, S, N, SE, SW, NE, NW (row_delta, col_delta)
_DIRECTIONS = [
    (0, 1), (0, -1), (1, 0), (-1, 0),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]

# Standard Boggle scoring by word length (letters after Q→QU expansion)
_SCORE_BY_LEN = {
    3: 1, 4: 1, 5: 2, 6: 3, 7: 5,
}
def _word_points(word_len):
    if word_len <= 7:
        return _SCORE_BY_LEN.get(word_len, 0)
    return 11  # 8+ letters


def _load_wordlist(path=None):
    """Load word list from file; return set of upper-case words (min length 3)."""
    if path is None:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "boggle_wordlist.txt")
    words = set()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip().upper()
                if w and not w.startswith("#") and len(w) >= 3 and w.isalpha():
                    words.add(w)
    return words


def _build_trie(words):
    """Build a trie for prefix lookups. Node is dict: '' key = is_word."""
    root = {}
    for w in words:
        node = root
        for c in w:
            node = node.setdefault(c, {})
        node[""] = True
    return root


# Minimal fallback words if no wordlist file (3–8 letters)
_FALLBACK_WORDS = """
ACE ACT ADD AGE AIM AIR ALL AND ANT ANY ARE ARM ART ASK ATE AWE AXE
BAD BAG BAN BAR BAT BAY BED BEE BET BIG BIT BOX BOY BUD BUG BUM BUS BUT BUY
CAB CAD CAN CAP CAR CAT CAW COB COD COG COT COW COX COY CRY CUB CUD CUE CUP CUR CUT
DAB DAD DAM DAM DAP DAY DEW DID DIE DIG DIM DIN DIP DOB DOE DOG DON DOT DOW DRY DUB DUD DUE DUG DUM DUN DUO DYE
EAR EAT EEL EGG EKE ELK ELM EME END ERE ERG ERR EWE EYE
FAD FAG FAN FAR FAT FAX FAY FED FEE FEN FER FEU FEW FEY FIG FIN FIR FIT FIX FLY FOB FOG FOP FOR FOU FOX FOY FRO FRY FUG FUN FUR
GAB GAD GAG GAP GAR GAT GAY GEL GEM GET GIG GIN GIP GIT GNU GOA GOB GOD GOO GOT GOV GOX GRR GUL GUM GUN GUT GUY GYM
HAD HAG HAH HAJ HAM HAN HAP HAS HAT HAW HAY HEH HEY HID HIE HIM HIN HIP HIS HIT HOB HOD HOE HOG HON HOP HOT HOW HOY HUB HUE HUG HUH HUM HUN HUP HUT
ICE ICK ICY IDS IFF IFS ILK ILL IMP INK INN INS ION IRE IRK IRK ISM ITS IVY
JAB JAG JAM JAR JAW JAY JEE JET JEU JIG JIN JOB JOG JOT JOW JOY JUG JUN JUS JUT
KAE KAF KAI KAS KAT KAY KEA KEF KEG KEN KEP KEX KEY KID KIF KIN KIP KIR KIS KIT KOA KOB KOI KOP KOR KOS KOW
LAB LAC LAD LAG LAH LAM LAP LAR LAS LAT LAV LAW LAX LAY LEA LED LEE LEG LEI LEK LEP LES LET LEU LEV LEW LEX LEY LEZ
MAD MAE MAG MAK MAN MAP MAR MAS MAT MAW MAX MAY MED MEE MEG MEL MEM MEN MES MET MEW MHO MIB MID MIG MIL MIM MIR MIS MIX MOA MOB MOD MOE MOG MOI MOL MOM MON MOO MOP MOR MOS MOT MOW MOZ MUD MUG MUM MUN MUX
NAB NAE NAG NAH NAM NAN NAP NAY NEE NEF NEG NEK NEP NET NEW NIB NID NIE NIL NIM NIP NIT NIX NOB NOD NOG NOH NOM NON NOO NOP NOR NOS NOT NOV NOW NOY NTH NUB NUN NUS NUT
OAF OAK OAR OAT OBA OBE OBI OBO OBS OCA OCH ODA ODD ODE ODS OES OFF OFT OHS OIK OIL OINK OKE OLD OLE OLM OLP OMB OMS ONE ONO ONS ONY OOF OOH OOP OOR OOT OPE OPS OPT OPUS ORB ORC ORD ORE ORF ORG ORS ORT OSE OUD OUK OUL OUP OUR OUS OUT OVA OWE OWL OWN OWR OWS OWT
PAD PAH PAK PAL PAM PAN PAP PAR PAS PAT PAW PAX PAY PEA PEC PED PEE PEG PEH PEL PEN PEP PER PES PET PEW PEZ PHA PHI PHO PHT PIA PIC PIE PIG PIN PIP PIR PIS PIT PIU PIX PLY POA POH POI POL POM POO POP POR POS POT POW POX POZ PRY PSI PST PUB PUD PUG PUL PUM PUN PUP PUR PUS PUT PUY PYA PYE
QAT QIS QUA
RAG RAH RAI RAJ RAK RAM RAN RAP RAT RAW RAX RAY REB REC RED REE REF REG REH REI REM REN REO REP RES RET REV REW REX REY REZ RHO RIA RIB RID RIF RIG RIM RIN RIP RIT RIZ ROB ROC ROD ROE ROG ROO ROOT ROP ROT ROW ROY RUB RUC RUD RUE RUG RUM RUN RUT RYA RYE
SAB SAC SAD SAE SAG SAI SAL SAM SAN SAP SAR SAS SAT SAU SAV SAW SAX SAY SEA SEC SED SEE SEG SEI SEL SEN SER SET SEW SEX SEY SEZ SHA SHE SHH SHY SIB SIC SIF SIG SIK SIM SIN SIP SIR SIS SIT SIX SKA SKI SKY SLY SLY SNA SNE SNO SNY SOB SOD SOG SOH SOL SOM SON SOO SOP SOT SOU SOW SOX SOY SPA SPY SRI STY SUB SUD SUE SUK SUL SUM SUN SUP SUQ SUR SUS SWY SYE SYN
TAB TAD TAE TAG TAI TAJ TAK TAM TAN TAO TAP TAR TAS TAT TAU TAV TAW TAX TAY TEA TEC TED TEE TEF TEG TEL TEN TEP TES TET TEW TEX THE THY TIC TID TIE TIG TIK TIL TIN TIP TIT TIX TOE TOG TOM TON TOO TOP TOR TOT TOW TOY TRY TSK TUB TUG TUI TUM TUN TUP TUX TWA TWO TWY TYE TYG
UDS UEY UGH UGS ULE ULU UMP UMS UNI UNS UPO UPP UPS URB URD URE URG URN URP URS USE USH USR UTA UTE UTS UVA
VAC VAE VAG VAN VAR VAS VAT VAU VAV VAW VAX VEE VEG VET VEX VIA VID VIE VIG VIM VIN VIS VOE VOL VOR VOW VOX VOZ VUG VUM
WAB WAD WAE WAG WAI WAN WAP WAR WAS WAT WAW WAX WAY WEE WEM WEN WET WEY WHA WHO WHY WIG WIN WIS WIT WOE WOG WOK WON WOO WOP WOS WOT WOW WOX WOY WRY WUD WUS WYE WYZ
YAG YAH YAK YAM YAP YAR YAW YAY YEA YEH YEN YEP YES YET YEW YEX YGO YID YIN YIP YOB YOD YOK YOM YON YOS YOW YUG YUK YUM YUP YUS YUX
ZAG ZAP ZAS ZAX ZEA ZED ZEE ZEK ZEL ZEP ZEX ZHO ZIN ZIP ZIT ZIZ ZOA ZOL ZOO ZOS ZOT ZOU ZOW ZUZ ZZZ
""".split()


def _default_wordlist():
    """Return default word set (fallback when no file)."""
    return set(w for w in _FALLBACK_WORDS if len(w) >= 3)


def _cell_char(grid, r, c):
    """One character at (r,c); Q stays Q (caller may expand to QU for matching)."""
    cell = grid[r][c]
    if isinstance(cell, str):
        return cell.upper()
    return str(cell).upper()


def _find_all_words(grid, height, width, trie, min_len=3):
    """DFS from each cell; return list of (word, path) with path = [(r,c), ...]."""
    found = {}  # word -> one path (we only need one path per word)
    n = height * width

    def dfs(r, c, node, path, word_chars):
        if not (0 <= r < height and 0 <= c < width):
            return
        if (r, c) in path:
            return
        ch = _cell_char(grid, r, c)
        if ch == "Q":
            seg = "QU"
        else:
            seg = ch
        for letter in seg:
            if letter not in node:
                return
            node = node[letter]
        new_path = path + [(r, c)]
        new_word = "".join(word_chars) + seg
        if len(new_word) >= min_len and node.get(""):
            found[new_word] = new_path
        # Recurse to neighbours with updated prefix
        prefix_chars = list(word_chars) + list(seg)
        for dr, dc in _DIRECTIONS:
            dfs(r + dr, c + dc, node, new_path, prefix_chars)

    for r in range(height):
        for c in range(width):
            dfs(r, c, trie, [], [])
    return list(found.items())


class BoggleSolver(BaseSolver):
    """Solver for Boggle puzzles.

    Input: info with "table" (2D grid of letters), "height", "width", "type" (easy/hard/extreme).
    Output: List of paths; each path is a list of (row, col) for one word, in order.
    Submitter uses same interface as WordsearchSubmitter (click path for each word).
    """

    # Percentage of total possible points needed to "solve" per difficulty
    TARGET_RATIO = {"easy": 0.30, "hard": 0.60, "extreme": 0.90}

    def __init__(self, info, show_progress=True, partial_solution_callback=None, progress_interval=10.0, partial_interval=100.0):
        super().__init__(
            info,
            show_progress=show_progress,
            partial_solution_callback=partial_solution_callback,
            progress_interval=progress_interval,
            partial_interval=partial_interval,
        )
        self.grid = [row[:] for row in info["table"]]
        wordlist_path = info.get("boggle_wordlist_path")
        words = _load_wordlist(wordlist_path) if wordlist_path else _load_wordlist()
        if not words:
            words = _default_wordlist()
        self.words = words
        self.trie = _build_trie(words)
        self.difficulty = (info.get("type") or "easy").lower()
        self.target_ratio = self.TARGET_RATIO.get(self.difficulty, 0.30)

    def solve(self):
        """Find words on the grid and return paths for enough words to reach target score."""
        if self.show_progress and self.progress_tracker:
            self._update_progress(
                words_found=0,
                total_words=0,
                current_phase="searching",
            )
        word_paths = _find_all_words(
            self.grid, self.height, self.width, self.trie, min_len=3
        )
        if not word_paths:
            return []
        # Score each word (by length after Q→QU)
        scored = []
        for word, path in word_paths:
            pts = _word_points(len(word))
            scored.append((pts, word, path))
        total_possible = sum(s[0] for s in scored)
        target = max(1, int(total_possible * self.target_ratio))
        # Greedy: take highest-point words first
        scored.sort(key=lambda x: (-x[0], -len(x[1])))
        chosen_paths = []
        running = 0
        for pts, word, path in scored:
            if running >= target:
                break
            chosen_paths.append(path)
            running += pts
        if self.show_progress and self.progress_tracker:
            self._update_progress(
                words_found=len(chosen_paths),
                total_words=len(word_paths),
                current_phase="done",
            )
        return chosen_paths
