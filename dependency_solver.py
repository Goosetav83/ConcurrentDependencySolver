import graphviz as gv
import sys

def transform_actions(actions: list[str], variables: list[str] | None = None) -> list[tuple[str, set[str]]]:
    '''
    zamienia akcje z postaci x := y + z na te potrzebne do klasy Dependency Solver

    @param actions: lista akcji w 'pisanym' formacie
    @param variables: opcjonalna lista zmiennych uzywanych w operacjach, jeżeli nie podana to brane pod uwage są male liczby alfabetu
    @return: Lista krotek (str, set[str]) gotowa do przekazania do konstruktora DependencySolver
    '''
    if variables is None:
        check = lambda x: x.isalpha
    else:
        check = lambda x: x in variables
    
    result = []

    for action in actions:
        left = action[0]
        i = action.find(':=')
        if i == -1: #Bad input, will be ignored
            continue
        #first right side char
        i +=2
        right = set()
        while i < len(action):
            if check(action[i]):
                right.add(action[i])
            i+=1
        result.append((left,right))

    return result

class DependencySolver:
    def __init__(self, actions : list[tuple[str, set[str]]], alphabet : list[str]):
        '''
        @param actions: lista wszystkich akcji w formacie (var_left_side, {vars_right_side}) (dla x := y+z -> ('x', {'y','z'}))
        @param alphabet: lista oznaczeń akcji ['a','b','c','d']
        '''
        self.actions = actions
        self.alphabet =alphabet
        self.deps = set()
        self.indeps = set()
        self.deps_dict = {a: set() for a in alphabet}
        self.__solve_dependency()

    def __solve_dependency(self):
        '''
        Określa zależnosci  między akcjami na przekazanym alfabecie
        '''
        for i in range(len(self.actions)):
            left,right = self.actions[i]
            char_i = self.alphabet[i]
            self.deps.add((char_i,char_i))
            for j in range(i+1, len(self.actions)):
                other_left,other_right = self.actions[j]
                char_j = self.alphabet[j]
                #Jeżeli zmieniają tą samą zmienną -> zależne, jeżeli iloczyn zbiorów zawiera jedna ze zmienianych ->zalezne
                #Jeżeli zmieniana w i-tym uzywana w j-tym lub j-ta w i-tym -> zalezne
                if left == other_left or any(x in (left,other_left) for x in right&other_right) or left in other_right or other_left in right:
                    self.deps.add((char_i, char_j))
                    self.deps.add((char_j, char_i))
                    self.deps_dict[char_i].add(char_j)
                    self.deps_dict[char_j].add(char_i)
                else:
                    self.indeps.add((char_i,char_j))
                    self.indeps.add((char_j,char_i))

    def __print_pipe(self, pipe, n):
        '''
        wypisuje krok algorytmu wyznaczania fnf

        @param pipe: słownik z listami algorytmu dla poszczególnych znaków alfabetu
        @param n: wysokość 'scian'
        '''
        check = lambda x,i: x[i] if len(x) > i else ' '

        for j in range(n,-1,-1):
            for a in self.alphabet:
                print('|' + check(pipe[a],j), end='')
            print('|')
        print()
    def create_fnf(self, w: str, print_steps = False) -> list[str]:
        '''
        Wyznacza postać normalną Foaty FNF dla śladu w

        @param w: ślad składający się z elementów alfabetu przekazanego do solvera
        @param print_steps: czy printować kolejne kroki algorytmu
        @return: FNF w postaci listy stringów
        '''
        
        pipes = {a: [] for a in self.alphabet}
        for char in w[::-1]:
            pipes[char].append(char)
            for dep in self.deps_dict[char]:
                pipes[dep].append('*')
            if print_steps:
                self.__print_pipe(pipes, len(w))
        result = []
        while any(pipes.values()):
            layer = ''
            for char in self.alphabet:
                if pipes[char] and pipes[char][-1] == char:
                    layer += char
            for x in layer:
                pipes[x].pop()
                for y in self.deps_dict[x]:
                    pipes[y].pop()
            result.append(layer)
            if print_steps and layer:
                print(f'Current layer: ({layer})')
                self.__print_pipe(pipes, len(w))
        return result
        
    def get_graph(self, w:str, path:str = 'graphs/w_word_graph.gv'):
        '''
        Utworzenie grafu zależności Diekerta

        @param w: słowo w dla którego tworzony jest graf
        @return: graf stworzony przy użyciu biblioteki graphviz
        '''
        dot = gv.Digraph(comment = f'Graph of \'{w}\'')
        for i in range(len(w)):
            dot.node(str(i), w[i])

        #node name == w.idx(char)

        graph = [[(w[i],w[j]) in self.deps and i<j for j in range(len(w))] for i in range(len(w))]
        graph = self.__longest_paths(graph)
        for i in range(len(w)):
            for j in range(len(w)):
                if graph[i][j] == 1:
                    dot.edge(str(i),str(j))

        dot.render(path) 

    def __longest_paths(self,graph: list[list[bool]]):
        '''
        znajduje najdluzsze sciezki w grafie

        @param graph: macierz krawedzi w formacie True/False
        @return: macierz odleglosci
        
        '''
        dp = [[1 if graph[i][j] else -float('inf') for j in range(len(graph))] for i in range(len(graph))]
        for i in range(len(graph)):
            dp[i][i] = 0
        for i in range(len(graph)-2,-1,-1):
            for j in range(len(graph)):
                for k in range(len(graph)):
                    if graph[i][k]:
                        dp[i][j] = max(dp[i][j],dp[i][k]+dp[k][j])

        return dp
    def get_sets(self) -> tuple[set[tuple[str,str]],set[tuple[str,str]]]:
        '''
        funkcja do pozyskania zbiorow zależnosci i niezaleznosci
        '''
        return self.deps, self.indeps

    def test_sets(self):
        '''
        funkcja testująca poprawność wyznaczonych zbiorów zależnosci i niezaleznosci
        '''
        assert all((b,a) in self.deps for (a,b) in self.deps), 'symetrycznosc1' #symetryczność
        assert all((b,a) in self.indeps for (a,b) in self.indeps), 'symetrycznosc2'#symetryczność
        assert all((a,a) in self.deps for a in self.alphabet),  'zwrotność'
        assert self.indeps.isdisjoint(self.deps), 'rozłączność' #rozłączność
            

def solve(paramstxt: str, path: str = 'graphs/w_word_graph.gv', print_steps: bool = False):
    '''
    funkcja do uruchomienia algorytmu z pliku tekstowego, wypisuje wyniki na standardowe wyjście oraz generuje graf Diekerta
    
    @param paramstxt: ścieżka do pliku z danymi wejściowymi
    @param path: ścieżka do zapisu grafu Diekerta (domyślnie 'graphs/w_word_graph.gv')
    @param print_steps: czy printować kroki pośrednie podczas tworzenia FNF
    '''
    with open(paramstxt,'r') as f:
        lines = f.readlines()
        actions = []
        alphabet = []
        w = ''
        variables = []
        current_section = None
        for line in lines:
            if line == '#actions\n':
                current_section = actions
                continue
            elif line == '#alphabet\n':
                current_section = alphabet
                continue
            elif line == '#w\n':
                current_section = w
                continue
            elif line == '#variables\n':
                current_section = variables
                continue
            else:
                if current_section is actions:
                    current_section.append(line.strip())
                elif current_section is alphabet:
                    current_section.append(line.strip())
                elif current_section is w:
                    w = line.strip()
                elif current_section is variables:
                    variables.append(line.strip())
        actions_transformed = transform_actions(actions, variables if variables else None)
        solver = DependencySolver(actions_transformed, alphabet)
        deps, indeps = solver.get_sets()
        print('Dependencies:')
        print(sorted(list(deps), key = lambda x: (ord(x[0]), ord(x[1])*10)))
        print()
        print('Independencies:')
        print(sorted(list(indeps), key = lambda x: (ord(x[0]), ord(x[1])*10)))
        print()
        print('FNF:')
        fnf = solver.create_fnf(w, print_steps)
        for layer in fnf:
            print(f'[{layer}]', end='')
        print()
        print('\nGenerating Diekert graph...')
        solver.get_graph(w, path)
        print(f'Graph generated as {path}.pdf')
        solver.test_sets()


if __name__ == '__main__':
    '''   
    Input
    (a) x := x + y
    (b) y := y + 2z
    (c) x := 3x + z
    (d) z := y - z
    • A = {a, b, c, d}
    • w = baadcb
    '''
    if len(sys.argv) > 1:
        file = sys.argv[1]
    else:
        file = 'param.txt'
    #solve('test1.txt', 'graphs/test1_graph.gv')
    #solve('test2.txt', 'graphs/test2_graph.gv')
    solve(file)