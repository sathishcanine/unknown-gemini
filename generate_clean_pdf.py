#!/usr/bin/env python3
"""
generate_clean_pdf.py
Generates an ultra-clean, spacious, elegant PDF containing ONLY:
Question (exact text) and Answer (direct, step-by-step).
No extra summaries, no promotional banners, no overlapping tables.
"""

import sys
import zlib

class CleanPDF:
    def __init__(self, filename):
        self.filename = filename
        self.pages = []
        self.current_ops = []
        self.width = 595.28   # A4
        self.height = 841.89
        self.left_margin = 50.0
        self.right_margin = 545.0
        self.usable_width = self.right_margin - self.left_margin # 495 pt
        self.top_margin = 785.0
        self.bottom_margin = 50.0
        self.y = self.top_margin
        self.page_count = 0

    def start_page(self):
        if self.current_ops:
            self.pages.append("".join(self.current_ops))
        self.current_ops = []
        self.page_count += 1
        self.y = self.top_margin

        # Subtle, clean running header
        self.draw_text("Monte Carlo & MCTS  --  Solved Examination Questions",
                       self.left_margin, 808, font='F2', size=8.5, color=(0.4, 0.4, 0.4))
        self.draw_line(self.left_margin, 802, self.right_margin, 802, color=(0.8, 0.8, 0.8), width=0.6)

    def ensure_space(self, pts):
        if self.y - pts < self.bottom_margin:
            self.start_page()

    def draw_text(self, text, x, y, font='F1', size=9.5, color=(0.1, 0.1, 0.1)):
        clean = self.sanitize(text)
        safe = clean.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        op = (f"BT\n"
              f"/{font} {size:.2f} Tf\n"
              f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg\n"
              f"1 0 0 1 {x:.2f} {y:.2f} Tm\n"
              f"({safe}) Tj\n"
              f"ET\n")
        self.current_ops.append(op)

    def draw_line(self, x1, y1, x2, y2, color=(0.7, 0.7, 0.7), width=0.6):
        op = f"{width:.2f} w {color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n"
        self.current_ops.append(op)

    def draw_rect(self, x, y, w, h, fill_color=None, stroke_color=None, line_width=0.6):
        ops = []
        if stroke_color:
            ops.append(f"{line_width:.2f} w {stroke_color[0]:.3f} {stroke_color[1]:.3f} {stroke_color[2]:.3f} RG\n")
        if fill_color:
            ops.append(f"{fill_color[0]:.3f} {fill_color[1]:.3f} {fill_color[2]:.3f} rg\n")
        ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re\n")
        if fill_color and stroke_color:
            ops.append("B\n")
        elif fill_color:
            ops.append("f\n")
        elif stroke_color:
            ops.append("S\n")
        self.current_ops.append("".join(ops))

    def sanitize(self, text):
        replacements = {
            '\u2014': ' -- ',
            '\u2013': '-',
            '\u2018': "'",
            '\u2019': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2192': '->',
            '\u03c0': 'pi',
            '\u03b3': 'gamma',
            '\u03b1': 'alpha',
            '\u03c1': 'rho',
            '\u03b5': 'epsilon',
            '\u2248': '~',
            '\u2265': '>=',
            '\u2264': '<=',
            '\u2211': 'sum',
            '\u220f': 'prod',
            '\u221a': 'sqrt',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def wrap_text(self, text, font, size, max_width):
        avg_char_w = size * (0.48 if font in ['F1', 'F3'] else 0.54 if font in ['F2'] else 0.58)
        max_chars = max(1, int(max_width / avg_char_w))
        result = []
        for raw in text.split('\n'):
            if not raw.strip():
                result.append("")
                continue
            words = raw.split(' ')
            cur = []
            cur_len = 0
            for w in words:
                w_len = len(w) + 1
                if cur_len + w_len - 1 <= max_chars:
                    cur.append(w)
                    cur_len += w_len
                else:
                    if cur:
                        result.append(" ".join(cur))
                    cur = [w]
                    cur_len = len(w)
            if cur:
                result.append(" ".join(cur))
        return result

    def print_text_block(self, text, font='F1', size=9.5, color=(0.15, 0.15, 0.15), x=None, width=None, line_h=13.5):
        if x is None: x = self.left_margin
        if width is None: width = self.usable_width
        lines = self.wrap_text(text, font, size, width)
        for line in lines:
            self.ensure_space(line_h)
            if line:
                self.draw_text(line, x, self.y, font=font, size=size, color=color)
            self.y -= line_h

    def add_question(self, label, q_text):
        padding = 7.0
        inner_w = self.usable_width - (2 * padding)
        lines = self.wrap_text(q_text, 'F3', 8.8, inner_w)
        box_h = (len(lines) * 11.8) + (2 * padding) + 2.0

        # Ensure question label + box stay together
        self.ensure_space(box_h + 30.0)
        self.y -= 8.0

        # Title / Label
        self.draw_text(label, self.left_margin, self.y, font='F2', size=10.0, color=(0.1, 0.2, 0.45))
        self.y -= 13.0

        # Background box
        self.draw_rect(self.left_margin, self.y - box_h, self.usable_width, box_h,
                       fill_color=(0.975, 0.98, 0.99), stroke_color=(0.82, 0.85, 0.90), line_width=0.6)

        cur_y = self.y - padding - 8.5
        for l in lines:
            if l:
                self.draw_text(l, self.left_margin + padding, cur_y, font='F3', size=8.8, color=(0.2, 0.22, 0.28))
            cur_y -= 11.8

        self.y -= (box_h + 8.0)

    def add_answer_heading(self):
        # Ensure answer heading and at least 5 lines of answer stay together
        self.ensure_space(75.0)
        self.draw_text("Answer:", self.left_margin, self.y, font='F2', size=9.8, color=(0.12, 0.45, 0.22))
        self.draw_line(self.left_margin, self.y - 2.0, self.left_margin + 42, self.y - 2.0, color=(0.12, 0.45, 0.22), width=0.8)
        self.y -= 12.0

    def add_divider(self):
        self.ensure_space(16.0)
        self.y -= 6.0
        self.draw_line(self.left_margin, self.y, self.right_margin, self.y, color=(0.88, 0.88, 0.88), width=0.5)
        self.y -= 10.0

    def save(self):
        if self.current_ops:
            self.pages.append("".join(self.current_ops))

        total_pages = len(self.pages)
        for p_idx in range(total_pages):
            page_num_str = f"Page {p_idx + 1} of {total_pages}"
            footer_op = (
                f"0.5 w 0.8 0.8 0.8 RG\n"
                f"{self.left_margin:.2f} 38.0 m {self.right_margin:.2f} 38.0 l S\n"
                f"BT\n/F1 8.5 Tf 0.45 0.45 0.45 rg\n"
                f"1 0 0 1 {self.left_margin:.2f} 26.0 Tm\n"
                f"(BITS Pilani -- AIMLCZG512 Deep Reinforcement Learning) Tj\n"
                f"ET\n"
                f"BT\n/F2 8.5 Tf 0.2 0.3 0.5 rg\n"
                f"1 0 0 1 {self.right_margin - 55:.2f} 26.0 Tm\n"
                f"({page_num_str}) Tj\n"
                f"ET\n"
            )
            self.pages[p_idx] = footer_op + self.pages[p_idx]

        objects = []
        obj_offsets = []

        def add_object(content):
            obj_num = len(objects) + 1
            objects.append(content)
            return obj_num

        add_object("<< /Type /Catalog /Pages 2 0 R >>")
        add_object(None)
        add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>")
        add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
        add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>")

        page_obj_ids = []
        for page_data in self.pages:
            stream_bytes = page_data.encode('latin1')
            comp = zlib.compress(stream_bytes)
            content_id = len(objects) + 1
            objects.append(f"<< /Length {len(comp)} /Filter /FlateDecode >>\nstream\n" + comp.decode('latin1') + "\nendstream")
            page_id = len(objects) + 1
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width:.2f} {self.height:.2f}]\n"
                f"   /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R /F5 7 0 R >> >>\n"
                f"   /Contents {content_id} 0 R >>"
            )
            objects.append(page_dict)
            page_obj_ids.append(page_id)

        kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>"

        out = []
        out.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        for idx, obj in enumerate(objects):
            offset = sum(len(chunk) for chunk in out)
            obj_offsets.append(offset)
            obj_num = idx + 1
            out.append(f"{obj_num} 0 obj\n".encode('latin1'))
            out.append(obj.encode('latin1'))
            out.append(b"\nendobj\n")

        xref_offset = sum(len(chunk) for chunk in out)
        total_objs = len(objects) + 1
        out.append(f"xref\n0 {total_objs}\n".encode('latin1'))
        out.append(b"0000000000 65535 f \n")
        for off in obj_offsets:
            out.append(f"{off:010d} 00000 n \n".encode('latin1'))

        out.append(f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode('latin1'))

        with open(self.filename, 'wb') as f:
            for chunk in out:
                f.write(chunk)
        print(f"Generated clean PDF: {self.filename} ({total_pages} pages)")


def build_clean_solutions():
    pdf = CleanPDF("AIMLCZG512_Monte_Carlo_Questions_and_Answers.pdf")
    pdf.start_page()

    # Simple clean title at top of Page 1
    pdf.draw_text("AIMLCZG512: Deep Reinforcement Learning", pdf.left_margin, pdf.y, font='F2', size=14.0, color=(0.1, 0.2, 0.45))
    pdf.y -= 16.0
    pdf.draw_text("Monte Carlo & MCTS -- All Exam Questions & Solutions", pdf.left_margin, pdf.y, font='F1', size=11.0, color=(0.3, 0.35, 0.45))
    pdf.y -= 10.0
    pdf.draw_line(pdf.left_margin, pdf.y, pdf.right_margin, pdf.y, color=(0.1, 0.2, 0.45), width=1.2)
    pdf.y -= 16.0

    # -------------------------------------------------------------------------
    # 1. Exam 1 - Q2(b)
    # -------------------------------------------------------------------------
    q1 = (
        "Q2(b) Consider the following four episodes of agent taking actions (left,right) until it reaches the terminal states:\n"
        "Episode #1: x, left, 16, x, right, 12, x,left, 16, T, 100\n"
        "Episode #2: x,left, 16, x, left, 16, x, right, 12,T, 200\n"
        "Episode #3: x, right, 15, x, right, 11, x,left, 13, T, 150\n"
        "Episode #4: x, right, 12, x,left, 16, x,left, 16, x, left, 16, x, 110\n"
        "Use first visit MC to estimate values of x and y [2 M]. Suggest two ways to encourage exploration [ No innovation here, "
        "only two from the classroom discussions accepted.] and explain [ One/Two Statements ] how they encourage exploration. [2 M].\n"
        "[The question asks to estimate x and y, but the episodes have only x, not y. So accept the answers only for x]"
    )
    pdf.add_question("Exam 1: Comprehensive Test (EC-3 Makeup -- 13-04-2024) -- Question 2(b) [4 Marks]", q1)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "1. First-Visit MC Value Estimation for x:\n"
        "In First-Visit Monte Carlo, return G is computed from the first occurrence of state x (t = 0) to termination.\n"
        "- Episode 1: G(1) = 16 + 12 + 16 + 100 = 144\n"
        "- Episode 2: G(2) = 16 + 16 + 12 + 200 = 244\n"
        "- Episode 3: G(3) = 15 + 11 + 13 + 150 = 189\n"
        "- Episode 4: G(4) = 12 + 16 + 16 + 16 + 110 = 170\n"
        "V(x) = (144 + 244 + 189 + 170) / 4 = 747 / 4 = 186.75\n"
        "State y: State y never appears in any episode, so V(y) cannot be estimated from the data.\n\n"
        "2. Two Ways to Encourage Exploration:\n"
        "- Exploring Starts (MCES): Every state-action pair has a non-zero probability of being selected as the initial start of an episode, ensuring all pairs are visited.\n"
        "- Epsilon-Greedy Policies: The agent selects the greedy action with probability (1 - epsilon) and picks a random action with probability epsilon, ensuring continuous exploration across all states.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 2. Exam 1 - Q4(c)
    # -------------------------------------------------------------------------
    q2 = (
        "Q4(c) Why should the action chosen by Monte Carlo Tree Search tend to be better than the action the underlying "
        "rollout policy would choose? [ One/Two Statements ] [2 M]."
    )
    pdf.add_question("Exam 1: Comprehensive Test (EC-3 Makeup -- 13-04-2024) -- Question 4(c) [2 Marks]", q2)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "MCTS acts as a policy improvement operator over the rollout policy:\n"
        "1. Lookahead vs. Local Heuristic: The rollout policy selects moves without lookahead, whereas MCTS builds an explicit multi-step search tree from the current state.\n"
        "2. Informed Statistical Aggregation: By focusing simulations on high-value paths using UCT and backpropagating simulated returns, selecting the root action with the highest visit count incorporates deep future outcomes, making it strictly superior to an unguided rollout policy action.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 3. Exam 1 - Q4(d)
    # -------------------------------------------------------------------------
    q3 = (
        "Q4(d) Assume you are using MCTS to decide the next move for the two-player game, with possible actions being up or down. "
        "Your present state is A, and you must decide between making an up or down move. Based on the iterations, understand the tree as "
        "a 2-player game tree. Let q be the estimated value and n be the number of visits to that state so far. Assume the moves are "
        "equi-probable if required. Explain how MCTS selects the next state for expansion [4.0 M].\n"
        "[Tree: Root A (n=9, q=-1); Child B (n=6, q=1 via 'up'); Child C (n=3, q=0 via 'down'); "
        "From B: F (n=3, q=-1 via 'up'), E (n=2, q=0 via 'down'); From E: H (n=1, q=1 via 'down')]"
    )
    pdf.add_question("Exam 1: Comprehensive Test (EC-3 Makeup -- 13-04-2024) -- Question 4(d) [4 Marks]", q3)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "1. Tree Policy & Selection Phase (UCT Formula):\n"
        "   Traverse the tree from Root A using UCT: UCT(s') = Q(s') + c * sqrt(ln(N(s)) / N(s')).\n"
        "   In a 2-player zero-sum game, Player 1 maximizes Player 1's value, while Player 2 minimizes Player 1's value (or maximizes -q).\n"
        "2. At Root A (Player 1, N = 9):\n"
        "   Player 1 evaluates child B (q = 1, n = 6) vs child C (q = 0, n = 3). Node B has higher value and dominant UCT, so Action 'up' to Node B is selected.\n"
        "3. At Node B (Player 2, N = 6):\n"
        "   Player 2 selects between F (q = -1, n = 3) and E (q = 0, n = 2). From Player 2's perspective, F is better (opponent score q = -1).\n"
        "4. Expansion Decision:\n"
        "   MCTS halts selection and triggers EXPANSION when it reaches a node with unvisited legal actions (n = 0).\n"
        "   At Node E, only action 'down' (to H) has been visited; action 'up' has never been expanded (n = 0). Therefore, MCTS selects this unvisited action from Node E, instantiates the new node in the tree, and starts a simulation rollout from it.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 4. Exam 2 - Q3(a)
    # -------------------------------------------------------------------------
    q4 = (
        "Q3(a) What are the two most important issues when you have to learn the value function using a first-visit "
        "Monte Carlo using for a deterministic policy.[2.0 M] Explain. Also, provide possible solutions. [1.5 M]."
    )
    pdf.add_question("Exam 2: Comprehensive Test (EC-3 Regular -- 06-06-2024) -- Question 3(a) [3.5 Marks]", q4)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "Issue 1: Lack of Exploration / Insufficient State-Action Coverage (1.0 M):\n"
        "- Explanation: With a deterministic policy, the agent takes the exact same action in each state. In deterministic environments, it follows identical paths every episode. Alternative actions are never sampled, preventing estimation of Q(s, a) for policy improvement.\n"
        "- Solutions (0.75 M): (i) Exploring Starts (MCES): Start each episode with a randomly chosen state-action pair with non-zero probability. (ii) Epsilon-Greedy Exploration: Choose random exploratory actions with probability epsilon.\n\n"
        "Issue 2: Infinite Loops / Inability to Reach Terminal State (1.0 M):\n"
        "- Explanation: Monte Carlo methods require complete episodes to compute returns. If a deterministic policy chooses actions leading into a cycle (e.g. s1 -> s2 -> s1), the agent loops forever and never terminates. No return can be calculated and learning stalls.\n"
        "- Solutions (0.75 M): (i) Episode Step Cutoff (Horizon Truncation): Terminate the episode after T_max steps. (ii) Epsilon Perturbation: Random actions break deterministic loops. (iii) Switch to TD Learning: TD bootstraps step-by-step without waiting for termination.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 5. Exam 2 - Q4(b)
    # -------------------------------------------------------------------------
    q5 = (
        "Q4(b) How does the MCTS ensure an action with the highest value is found in real-time? If the best action can "
        "be selected only by MCTS, why is any prior learning of Q(s,a) required? [2.0 M]"
    )
    pdf.add_question("Exam 2: Comprehensive Test (EC-3 Regular -- 06-06-2024) -- Question 4(b) [2 Marks]", q5)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "1. How MCTS Finds the Highest-Value Action in Real-Time (1.0 M):\n"
        "MCTS conducts asymmetric lookahead search from the root. Using UCT, it dynamically concentrates search budget on the most promising branches. As simulated trajectories accumulate within the real-time turn budget, visit counts of optimal branches grow exponentially faster, converging to the best action at the root.\n\n"
        "2. Why Prior Learning of Q(s, a) / Value Network is Required (1.0 M):\n"
        "- Truncates Rollouts: In games with huge state spaces (e.g. Go), running random rollouts to the end is computationally intractable and has extreme variance. A learned value network evaluates leaf positions immediately without full rollouts.\n"
        "- Guides Search: A learned policy prior P(s, a) directs early iterations toward strong moves, pruning obvious blunders from the outset.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 6. Exam 3 - Q2(c)
    # -------------------------------------------------------------------------
    q6 = (
        "Q2(c) The robot executes the policy pi (Continue at M, Recharge at L) and generates the following episode with gamma = 0.9:\n"
        "Episode: (M, Continue,+1, M) -> (M, Continue, +1, L) -> (L, Recharge, -3, M) -> (M, Continue, +1, Terminal).\n"
        "Using First-Visit Monte Carlo, calculate the estimated value V(M) from this single episode. Show the return calculation with proper discounting. [1 Mark]"
    )
    pdf.add_question("Exam 3: Question Bank / Midsem -- Question 2(c) [1 Mark]", q6)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "Episode Sequence (gamma = 0.9):\n"
        "- t = 0: S_0 = M, A_0 = Continue, R_1 = +1\n"
        "- t = 1: S_1 = M, A_1 = Continue, R_2 = +1\n"
        "- t = 2: S_2 = L, A_2 = Recharge, R_3 = -3\n"
        "- t = 3: S_3 = M, A_3 = Continue, R_4 = +1, S_4 = Terminal\n\n"
        "First-Visit MC Rule: Calculate return G only from the FIRST occurrence of M (at t = 0):\n"
        "G_0 = R_1 + gamma * R_2 + (gamma^2) * R_3 + (gamma^3) * R_4\n"
        "G_0 = (+1) + 0.9*(+1) + (0.9)^2*(-3) + (0.9)^3*(+1)\n"
        "G_0 = 1.0 + 0.9 - 2.43 + 0.729 = +0.199\n\n"
        "Estimated Value: V(M) = G_0 = +0.199",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 7. Exam 3 - Q2(d)
    # -------------------------------------------------------------------------
    q7 = (
        "Q2(d) The robot now uses an exploratory behaviour policy b where: b(Continue | M) = 0.7; b(Recharge | M) = 0.3. "
        "The target policy pi is deterministic: pi(Continue | M) = 1.0. Consider the following episode under behavior policy b with gamma = 0.9:\n"
        "Episode: (M, Continue, +1, M) -> (M, Recharge, -2, H) -> (H, Continue, +2, Terminal).\n"
        "Calculate:\n"
        "d-1) The importance sampling ratio rho from the first occurrence of state M until termination\n"
        "d-2) The return G from state M\n"
        "d-3) Explain how this ratio would be used in weighted importance sampling to update V(M) [3 Marks]"
    )
    pdf.add_question("Exam 3: Question Bank / Midsem -- Question 2(d) [3 Marks]", q7)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "d-1) Importance Sampling Ratio rho (1 Mark):\n"
        "rho = prod_{k=0}^{2} [ pi(A_k | S_k) / b(A_k | S_k) ]\n"
        "- At t = 0 (M, Continue): pi / b = 1.0 / 0.7\n"
        "- At t = 1 (M, Recharge): pi(Recharge | M) = 0.0 (since target pi is deterministic Continue), b = 0.3 => Ratio = 0.0 / 0.3 = 0\n"
        "- At t = 2 (H, Continue): Ratio = 1.0\n"
        "rho = (1.0 / 0.7) * (0.0 / 0.3) * 1.0 = 0.0\n\n"
        "d-2) Return G from State M (1 Mark):\n"
        "G = R_1 + gamma * R_2 + (gamma^2) * R_3 = (+1) + 0.9*(-2) + (0.9)^2*(+2) = 1.0 - 1.8 + 1.62 = +0.82\n\n"
        "d-3) Weighted Importance Sampling Update (1 Mark):\n"
        "In Weighted Importance Sampling: V(M) = sum(rho_i * G_i) / sum(rho_i).\n"
        "Update rule: V_{n+1} = V_n + (W / C_n) * (G - V_n) where weight W = rho.\n"
        "Since rho = 0 (weight W = 0), this episode adds 0 to numerator and denominator, leaving V(M) completely unchanged. This correctly reflects that an action impossible under pi provides zero information about pi.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 8. Exam 3 - Q4(a)
    # -------------------------------------------------------------------------
    q8 = (
        "Q4(a) During the Selection phase of Monte Carlo Tree Search, a node corresponding to state s has two available actions, "
        "a_1 and a_2. The stored statistics are:\n"
        "Action a_1: Visits N(s, a_1) = 4,  Mean value Q(s, a_1) = 0.60\n"
        "Action a_2: Visits N(s, a_2) = 16, Mean value Q(s, a_2) = 0.65\n"
        "Compute the UCB score for both actions. Which action will be selected next? Justify numerically [3 Marks]"
    )
    pdf.add_question("Exam 3: Question Bank / Midsem -- Question 4(a) [3 Marks]", q8)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "Total Visits to state s: N(s) = 4 + 16 = 20, ln(20) = 2.99573\n"
        "Formula: UCB(s, a) = Q(s, a) + c * sqrt(ln(N(s)) / N(s, a))\n\n"
        "For c = 1.0:\n"
        "- Action a_1: UCB(s, a_1) = 0.60 + 1.0 * sqrt(2.99573 / 4) = 0.60 + 0.8654 = 1.4654\n"
        "- Action a_2: UCB(s, a_2) = 0.65 + 1.0 * sqrt(2.99573 / 16) = 0.65 + 0.4327 = 1.0827\n\n"
        "For c = sqrt(2) ~ 1.414:\n"
        "- Action a_1: UCB(s, a_1) = 0.60 + 1.414 * 0.8654 = 0.60 + 1.2238 = 1.8238\n"
        "- Action a_2: UCB(s, a_2) = 0.65 + 1.414 * 0.4327 = 0.65 + 0.6119 = 1.2619\n\n"
        "Selected Action: Action a_1 will be selected next.\n"
        "Justification: Even though a_2 has a slightly higher mean value (0.65 vs 0.60), action a_1 has been visited far fewer times (4 vs 16), giving it a much larger exploration bonus (0.865 vs 0.433) that dominates selection.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 9. Exam 3 - Q4(c)
    # -------------------------------------------------------------------------
    q9 = (
        "Q4(c) The MCTS algorithm is inspired by AlphaGo and AlphaZero. State one key difference between AlphaGo and "
        "AlphaZero regarding their training data. Why does this make AlphaZero more generalizable to other domains? [2 Marks]"
    )
    pdf.add_question("Exam 3: Question Bank / Midsem -- Question 4(c) [2 Marks]", q9)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "1. Key Difference in Training Data (1.0 M):\n"
        "- AlphaGo: Trained using supervised learning on ~30 million human expert moves, followed by RL self-play.\n"
        "- AlphaZero: Trained tabula rasa (from scratch) with zero human demonstration data, learning purely from self-play RL given only basic game rules.\n\n"
        "2. Why AlphaZero is More Generalizable (1.0 M):\n"
        "- Eliminates data dependency: Does not require large, expensive human expert datasets (which do not exist in most real-world problems).\n"
        "- Removes human bias: Learns unconstrained by human suboptimal play patterns.\n"
        "- Universal architecture: The same framework generalized across Go, Chess, and Shogi without game-specific modifications.",
        line_h=12.2
    )
    pdf.add_divider()

    # -------------------------------------------------------------------------
    # 10. Exam 4 - Question 5
    # -------------------------------------------------------------------------
    q10 = (
        "Question 5 [2 + 2 + 2 + 1 = 7 Marks]\n"
        "You are applying Monte Carlo Tree Search (MCTS) to a two-player game. At the root node, there are two available child nodes, "
        "denoted C1 and C2. Each child has been visited a certain number of times and has associated returns from simulated rollouts. "
        "So far, node C1 has been visited 2 times with observed returns of 5 and 7, while node C2 has been visited once with an observed "
        "return of 4. The total number of visits to the root is 3.\n\n"
        "The tree policy being used is the Upper Confidence Bound (UCB) algorithm with exploration constant c=1, which governs how child "
        "nodes are selected within the search tree. The rollout policy being used is a simple random simulation policy, where after leaving "
        "the known tree structure, actions are chosen uniformly at random until a terminal state is reached.\n\n"
        "a) Using the standard backup rule in MCTS, compute the current average value (mean return) for nodes C1 and C2 based on the rollout "
        "values observed so far. (2 Marks)\n"
        "b) Apply the UCB algorithm as the tree policy to compute the UCB score for both C1 and C2. Based on these scores, identify which child "
        "node will be selected next for simulation. (2 Marks)\n"
        "c) Suppose the next simulation is run directly from C2 using the random rollout policy (no expansion is performed at this step), "
        "and the rollout returns a value of 8. Show how the backup value (average return) of C2 is updated after this additional simulation, "
        "and state its new average. (2 Marks)\n"
        "d) Briefly state the role of Monte Carlo Tree Search (MCTS) in AlphaGo and why it was significant for its success. (1 Mark)"
    )
    pdf.add_question("Exam 4: Comprehensive Exam (EC-3 Regular -- 07-09-2025) -- Question 5 [7 Marks]", q10)
    pdf.add_answer_heading()
    pdf.print_text_block(
        "Part a) Mean Return for C1 and C2 (2 Marks):\n"
        "- Node C1: Visited N(C1) = 2, returns = 5, 7  =>  Q(C1) = (5 + 7) / 2 = 12 / 2 = 6.0\n"
        "- Node C2: Visited N(C2) = 1, return = 4       =>  Q(C2) = 4 / 1 = 4.0\n\n"
        "Part b) UCB Score & Selection with c = 1.0 (2 Marks):\n"
        "Formula: UCB(Ci) = Q(Ci) + c * sqrt(ln(N_root) / N(Ci)), with N_root = 3, ln(3) = 1.098612\n"
        "- Node C1: UCB(C1) = 6.0 + 1.0 * sqrt(1.098612 / 2) = 6.0 + 0.74115 = 6.7412\n"
        "- Node C2: UCB(C2) = 4.0 + 1.0 * sqrt(1.098612 / 1) = 4.0 + 1.04815 = 5.0482\n"
        "Decision: Since UCB(C1) = 6.7412 > UCB(C2) = 5.0482, Node C1 will be selected next for simulation.\n\n"
        "Part c) Backup Value Update for C2 after Rollout Return of 8 (2 Marks):\n"
        "- Previous visits: N_old = 1, previous return = 4\n"
        "- New return: R = 8\n"
        "- New visits: N_new = 1 + 1 = 2\n"
        "- New Total Return = 4 + 8 = 12\n"
        "- Updated Average: Q_new(C2) = 12 / 2 = 6.0\n"
        "(Or via incremental formula: Q_new = 4.0 + (8 - 4.0)/2 = 4.0 + 2.0 = 6.0)\n\n"
        "Part d) Role of MCTS in AlphaGo and Significance (1 Mark):\n"
        "- Role: Central lookahead search engine combining Policy Network priors (to guide and narrow search width) with Value Network and rollout evaluations (to truncate search depth).\n"
        "- Significance: Provides rigorous forward verification and minimax lookahead, preventing tactical blunders and enabling superhuman performance.",
        line_h=12.2
    )

    pdf.save()

if __name__ == '__main__':
    build_clean_solutions()
