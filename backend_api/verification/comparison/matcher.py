import math
import re

prefix_regex = re.compile(r'(?i)\b(dr|dr\.|doctor|prof|prof\.|mr|mrs|ms)\b')
non_alpha_num_regex = re.compile(r'[^a-z0-9\s]')
multi_space_regex = re.compile(r'\s+')

def normalize_name(name: str) -> str:
    lower = name.lower()
    stripped_prefix = prefix_regex.sub("", lower)
    clean_alpha = non_alpha_num_regex.sub(" ", stripped_prefix)
    single_space = multi_space_regex.sub(" ", clean_alpha)
    return single_space.strip()

def jaro_winkler_similarity(s1: str, s2: str) -> float:
    n1 = normalize_name(s1)
    n2 = normalize_name(s2)

    if n1 == n2:
        return 1.0
    if len(n1) == 0 or len(n2) == 0:
        return 0.0

    match_distance = int(math.floor(max(len(n1), len(n2)) / 2.0)) - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len(n1)
    s2_matches = [False] * len(n2)

    matches = 0
    for i in range(len(n1)):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(n2))

        for j in range(start, end):
            if s2_matches[j]:
                continue
            if n1[i] != n2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    t = 0.0
    k = 0
    for i in range(len(n1)):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if n1[i] != n2[k]:
            t += 0.5
        k += 1

    m = float(matches)
    jaro = (m / len(n1) + m / len(n2) + (m - t) / m) / 3.0

    prefix_length = 0
    max_prefix = min(4, min(len(n1), len(n2)))
    for i in range(max_prefix):
        if n1[i] == n2[i]:
            prefix_length += 1
        else:
            break

    return jaro + float(prefix_length) * 0.1 * (1.0 - jaro)

def calculate_name_match_percentage(name1: str, name2: str) -> float:
    similarity = jaro_winkler_similarity(name1, name2)
    return round(similarity * 10000.0) / 100.0
