# from app.codes import generate_judge_code, is_valid_judge_code


# def test_generated_codes_validate() -> None:
#     for _ in range(1000):
#         code = generate_judge_code()
#         assert len(code) == 8
#         assert is_valid_judge_code(code)


# def test_excludes_ambiguous_chars() -> None:
#     forbidden = set("01OIL")
#     for _ in range(1000):
#         assert not (set(generate_judge_code()) & forbidden)


# def test_single_char_typo_is_caught() -> None:
#     code = generate_judge_code()
#     # Flip the 4th character to something different in the charset.
#     from app.codes import CHARSET

#     swap = next(c for c in CHARSET if c != code[3])
#     bad = code[:3] + swap + code[4:]
#     assert not is_valid_judge_code(bad)


# def test_dashed_format_accepted() -> None:
#     code = generate_judge_code()
#     dashed = f"{code[:4]}-{code[4:]}"
#     assert is_valid_judge_code(dashed)
