from typing import List


def match(pattern: List[str], source: List[str]) -> List[str]:
    """Attempt to match pattern to source

    % matches a sequence of zero or more words and _ matches any single word

    Args:
        pattern - a pattern using to % and/or _ to extract words from the source
        source - a phrase represented as a list of words (strings)

    Returns:
        None if the pattern and source do not "match" ELSE A list of matched words
        (words in the source corresponding to _'s or %'s, in the pattern, if any)
    """
    sind = 0  # current index we are looking at in the source list
    pind = 0  # current index we are looking at in the pattern list
    result: List[str] = []  # to store the substitutions that we will return if matched

    # keep checking as long as we haven't hit the end of both pattern and source while
    # pind is still a valid index OR sind is still a valid index (valid index means that
    # the index is != to the length of the list)
    while pind != len(pattern) or sind != len(source):
        # 1) check to see if we are at the end of the pattern (from the while condition
        # we know since we already checked to see if you were at the end of the pattern
        # and the source, then you know that if this is True, then the pattern has
        # ended, but the source has not) if we reached the end of the pattern but not
        # source then no match
        if pind == len(pattern):
            return None

        # 2) check to see if the current thing in the pattern is a %
        elif pattern[pind] == "%":
            # at end of pattern grab the rest of the source
            if pind == (len(pattern) - 1):
                return result + [" ".join(source[sind:])]
            else:
                accum = ""
                pind += 1
                while pattern[pind].lower() != source[sind].lower():
                    accum += " " + source[sind]
                    sind += 1

                    # abort in case we've run out of source with more pattern left
                    if sind >= len(source):
                        return None

                result.append(accum.strip())

        # 3) if we reached the end of the source but not pattern then no match
        elif sind == len(source):
            return None

        # 4) check to see if the current thing in the pattern is an _
        elif pattern[pind] == "_":
            # neither has ended: add a singleton
            result += [source[sind].strip()]
            pind += 1
            sind += 1

        # 5) check to see if the current thing in the pattern is the same as the current
        # thing in the source
        elif pattern[pind].lower() == source[sind].lower():
            # neither has ended and the words match, continue checking
            pind += 1
            sind += 1

        # 6) this will happen if none of the other conditions are met
        else:
            # neither has ended and the words do not match, no match
            return None

    return result