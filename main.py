from match import match
from typing import List, Tuple, Callable, Any

# Action functions must be defined BEFORE pa_list
def game_by_year(matches: List[str]) -> List[str]:
    """Returns games made in a specific year."""
    year = matches[0]
    return [f"Games made in {year}: Game A, Game B"]

def game_by_year_range(matches: List[str]) -> List[str]:
    """Returns games made between two years."""
    year1, year2 = matches[0], matches[1]
    return [f"Games made between {year1} and {year2}: Game C, Game D"]

def game_before_year(matches: List[str]) -> List[str]:
    """Returns games made before a specific year."""
    year = matches[0]
    return [f"Games made before {year}: Game E, Game F"]

def game_after_year(matches: List[str]) -> List[str]:
    """Returns games made after a specific year."""
    year = matches[0]
    return [f"Games made after {year}: Game G, Game H"]

def maker_by_game(matches: List[str]) -> List[str]:
    """Returns the maker of a specific game."""
    game = matches[0]
    return [f"The maker of {game}: Studio X"]

def game_by_maker(matches: List[str]) -> List[str]:
    """Returns games made by a specific maker."""
    maker = matches[0]
    return [f"Games made by {maker}: Game I, Game J"]

def year_by_game(matches: List[str]) -> List[str]:
    """Returns the year a game was made."""
    game = matches[0]
    return [f"{game} was made in: 2020"]

def bye_action(matches: List[str]) -> List[str]:
    return ["Goodbye!"]

# The pattern-action list for the natural language query system
# A list of tuples of pattern and action
pa_list: List[Tuple[List[str], Callable[[List[str]], List[Any]]]] = [
    (str.split("what games were made in _"), game_by_year),
    (str.split("what games were made between _ and _"), game_by_year_range),
    (str.split("what games were made before _"), game_before_year),
    (str.split("what games were made after _"), game_after_year),
    (str.split("who made %"), maker_by_game),
    (str.split("what games were made by %"), game_by_maker),
    (str.split("when was % made"), year_by_game),
    (["bye"], bye_action),
]

def search_pa_list(src: List[str]) -> List[str]:
    """Takes source, finds matching pattern and calls corresponding action. If it finds
    a match but has no answers it returns ["No answers"]. If it finds no match it
    returns ["I don't understand"].

    Args:
        source - a phrase represented as a list of words (strings)

    Returns:
        a list of answers. Will be ["I don't understand"] if it finds no matches and
        ["No answers"] if it finds a match but no answers
    """
    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            answer = act(mat)
            return answer if answer else ["No answers"]
    return ["I don't understand"]

def query_loop() -> None:
    """The simple query loop. The try/except structure is to catch Ctrl-C or Ctrl-D
    characters and exit gracefully.
    """
    print("Welcome to the game database!\n")
    while True:
        try:
            print()
            query = input("Your query? ").replace("?", "").lower().split()
            
            # Check for exit condition
            if query == ["bye"]:
                print("\nSo long!\n")
                break
            
            

        except (KeyboardInterrupt, EOFError):
            break
    

def main():
    """Main entry point for the program."""
    query_loop()

if __name__ == "__main__":
    main()