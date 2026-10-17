# Robo Rallye — diagrammes UML

Sources Mermaid des diagrammes du rapport (`docs/Rapport_Robo_Rally.docx`), à jour avec le code final.
Ils s’affichent directement sur GitHub, ou dans VS Code avec l’extension « Markdown Preview Mermaid Support».

## Architecture en couches

```mermaid
flowchart TB
  UI["<b>ui</b> : interface Tkinter<br/>RoboRallyApp · BoardView · ProgramPanel · Assets"]
  AI["<b>ai</b> : choix des cartes (Strategy)<br/>RandomStrategy · HumanStrategy · PerceptronStrategy<br/>simulate() · extract() · Perceptron · DistanceMap"]
  ENG["<b>engine</b> : règles et boucle de jeu<br/>Game (phases du tour) · RulesEngine (règles) · EventBus"]
  MOD["<b>model</b> : données du jeu<br/>GameState · Board · Tile · Robot · Team · Card · Deck"]
  MAP[("maps/level1.txt")]
  CFG[["config.py<br/>paramètres"]]
  UI -- "crée la partie, choisit les joueurs" --> AI
  UI -- "step(), submit_program()" --> ENG
  AI -- "simule sur une copie" --> ENG
  ENG -- "lit et modifie" --> MOD
  MAP -- "Board.from_file()" --> MOD
  CFG -.- ENG
  ENG -. "événements (Observer)" .-> UI
```

## Diagramme de classes : modèle

```mermaid
classDiagram
  direction TB
  class Direction {
    <<enumeration>>
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    +rotate(r: Rotation) Direction
    +turn_right() Direction
    +turn_left() Direction
    +opposite() Direction
    +delta() tuple
  }
  class Rotation {
    <<enumeration>>
    RIGHT = +1
    LEFT = -1
    U_TURN = +2
  }
  class Position {
    <<frozen dataclass>>
    +x int
    +y int
    +step(d, n) Position
    +manhattan(p) int
  }
  class GameState {
    +board Board
    +teams list~Team~
    +turn int
    +winner Team
    +over bool
    +used_bonuses set~Position~
    +new_game(board)$ GameState
    +robot_at(p) Robot
    +bonus_available(p) bool
    +clone() GameState
    +render() str
  }
  class Board {
    +SIZE = 12
    +checkpoints dict
    +from_file(path)$ Board
    +tile_at(p) Tile
    +in_bounds(p) bool
  }
  class Team {
    +id int
    +robots list~Robot~
    +has_won() bool
    +is_out() bool
  }
  class Robot {
    +id str
    +team_id int
    +position Position
    +direction Direction
    +status RobotStatus
    +next_cp int
    +bonuses list~BonusType~
    +program list~Card~
    +validate_checkpoint(n) bool
    +use_bonus(b) bool
    +finished() bool
    +copy() Robot
  }
  class RobotStatus {
    <<enumeration>>
    ACTIVE
    DAMAGED
    ELIMINATED
  }
  class Tile {
    <<abstract>>
    +blocks() bool
    +is_hole() bool
    +symbol str
  }
  class NormalTile
  class WallTile
  class HoleTile
  class ConveyorTile {
    +direction Direction
    +turn Rotation
  }
  class BonusTile {
    +bonus BonusType
  }
  class CheckpointTile {
    +number int
  }
  class BonusType {
    <<enumeration>>
    SHIELD
    BOOST
    REPAIR
    JUMP
  }

  GameState "1" o-- "1" Board
  GameState "1" *-- "2" Team
  Team "1" *-- "2" Robot
  Board "1" *-- "144" Tile
  Robot --> Position
  Robot --> Direction
  Robot --> RobotStatus
  Robot ..> BonusType
  Direction ..> Rotation
  Tile <|-- NormalTile
  Tile <|-- WallTile
  Tile <|-- HoleTile
  Tile <|-- ConveyorTile
  Tile <|-- BonusTile
  Tile <|-- CheckpointTile
  BonusTile --> BonusType
```

## Diagramme de classes : moteur, cartes et IA

```mermaid
classDiagram
  direction TB
  class Card {
    <<abstract>>
    +name str
    +execute(robot, engine)
  }
  class MoveCard {
    +steps int
  }
  class BackUpCard
  class TurnCard {
    +rotation Rotation
  }
  class Deck {
    -draw_pile list
    -discard list
    +draw(n) list~Card~
    +discard_all(cards)
  }
  class Game {
    +state GameState
    +engine RulesEngine
    +phase Phase
    +decks dict
    +hands dict
    +step() bool
    +play_turn()
    +play_to_end()
    +submit_program(id, cards)
    +waiting_for() list
    +play_order() list
  }
  class Phase {
    <<abstract>>
    +run(game) Phase
  }
  class DrawPhase
  class ProgrammingPhase
  class CardPhase
  class EndOfTurnPhase
  class GameOverPhase
  class RulesEngine {
    +execute_card(robot, card)
    +move(robot, d, steps) int
    +rotate(robot, r)
    +try_step(robot, d) StepResult
    +push(robot, d) bool
    +activate_conveyors()
    +check_victory() bool
    +publish(type, robot)
  }
  class EventBus {
    +subscribe(listener, type)
    +publish(event)
  }
  class Strategy {
    <<interface>>
    +interactive bool
    +choose(state, robot, hand, size) list
  }
  class RandomStrategy
  class HumanStrategy
  class PerceptronStrategy {
    +perceptron Perceptron
    +choose(...) list
  }
  class Perceptron {
    +weights list~float~
    +bias float
    +score(x) float
    +save() / load()
  }
  class DistanceMap {
    +distance(p, cp) int
    +remaining(p, next_cp) int
  }

  Card <|-- MoveCard
  Card <|-- BackUpCard
  Card <|-- TurnCard
  Deck o-- Card
  Game --> RulesEngine
  Game --> Phase
  Game --> Deck
  Game --> Strategy
  Phase <|-- DrawPhase
  Phase <|-- ProgrammingPhase
  Phase <|-- CardPhase
  Phase <|-- EndOfTurnPhase
  Phase <|-- GameOverPhase
  Card ..> RulesEngine : execute() appelle
  RulesEngine --> EventBus
  Strategy <|.. RandomStrategy
  Strategy <|.. HumanStrategy
  Strategy <|.. PerceptronStrategy
  PerceptronStrategy --> Perceptron
  PerceptronStrategy --> DistanceMap
  PerceptronStrategy ..> RulesEngine : simulation sur une copie
```

## Diagramme d’états : un tour de jeu

```mermaid
stateDiagram-v2
  [*] --> Draw : new_game()
  Draw --> Programming : tour += 1, chaque robot pioche 5 cartes
  Programming --> Programming : un joueur humain n'a pas encore choisi
  Programming --> Cards : chaque robot a verrouillé son programme
  state Cards {
    [*] --> Registre1
    Registre1 --> Registre2 : tous les robots ont joué la carte 1
    Registre2 --> Registre3 : tous les robots ont joué la carte 2
    Registre3 --> [*] : tous les robots ont joué la carte 3
  }
  Cards --> GameOver : victoire après une carte
  Cards --> EndOfTurn
  EndOfTurn --> GameOver : victoire, égalité ou limite de 100 tours
  EndOfTurn --> Draw : tapis roulants activés, cartes défaussées
  GameOver --> [*]
```

## Diagramme d’états : un robot

```mermaid
stateDiagram-v2
  [*] --> SurLePlateau : placé sur sa case de départ
  state SurLePlateau {
    [*] --> Active
    Active --> Damaged : poussé contre un mur
    Damaged --> Active : kit de réparation
    --
    [*] --> VersCP1
    VersCP1 --> VersCP2 : franchit CP1
    VersCP2 --> VersCP3 : franchit CP2
    VersCP3 --> Arrivé : franchit CP3
    Arrivé --> Arrivé : continue pour aider son équipier
  }
  SurLePlateau --> Eliminated : trou ou sortie du plateau
  Eliminated --> [*]
```

## Diagramme de séquence : un tour complet

```mermaid
sequenceDiagram
  autonumber
  participant APP as RoboRallyApp
  participant G as Game
  participant D as Deck
  participant S as Strategy
  participant RE as RulesEngine
  participant EB as EventBus

  APP->>G: step()
  Note over G: DrawPhase
  loop chaque robot sur le plateau
    G->>D: draw(5)
    D-->>G: main
  end
  APP->>G: step()
  Note over G: ProgrammingPhase
  loop chaque robot sur le plateau
    G->>S: choose(state, robot, main, 3)
    S-->>G: [c1, c2, c3]  (None si humain)
  end
  opt joueur humain
    APP->>G: submit_program(id, cartes)
  end
  Note over G: CardPhase : un step() = une carte
  loop registre 1..3, robots dans l'ordre du tour
    APP->>G: step()
    G->>RE: execute_card(robot, carte)
    RE-)EB: MOVED / PUSHED / ELIMINATED / CHECKPOINT
    EB-)APP: journal mis à jour
    APP->>APP: redessiner le plateau
  end
  Note over G: EndOfTurnPhase
  G->>RE: activate_conveyors()
  G->>RE: check_victory()
  alt une équipe a gagné
    RE-)EB: GAME_WON
  else la partie continue
    G->>D: discard_all(cartes jouées)
  end
```

## Diagramme de séquence : poussée dans un trou

```mermaid
sequenceDiagram
  autonumber
  participant RE as RulesEngine
  participant B as Board
  participant A as R1_E1 (pousse)
  participant P as R2_E2 (poussé)

  Note over A: joue « Move 2 », orienté EST en (3,5)
  RE->>B: tile_at(4,5)
  B-->>RE: case normale, libre
  RE->>A: position = (4,5)
  RE->>B: tile_at(5,5)
  B-->>RE: case normale, occupée par P
  RE->>RE: push(P, EST)
  alt P possède un bouclier
    RE->>P: bouclier consommé, P ne bouge pas
    RE-->>A: BLOCKED : fin de la carte
  else pas de bouclier
    RE->>B: tile_at(6,5)
    B-->>RE: trou
    RE->>P: status = ELIMINATED
    RE->>A: position = (5,5)
  end
  RE->>RE: check_checkpoint(A)
```

## Algorithme : try_step

```mermaid
flowchart TD
  A(["try_step(robot, d)"]) --> B["cible = position + d"]
  B --> C{"cible dans<br/>0..11 ?"}
  C -- non --> X["éliminer le robot"] --> RF(["FELL"])
  C -- oui --> J{"mur ou trou<br/>et bonus Saut<br/>et atterrissage sûr ?"}
  J -- oui --> JJ["utiliser le Saut<br/>position = cible + d"] --> K
  J -- non --> W{"cible = mur ?"}
  W -- oui --> RB(["BLOCKED<br/>reste de la carte annulé"])
  W -- non --> O{"robot Q<br/>sur la cible ?"}
  O -- oui --> P[["push(Q, d)"]]
  P --> PO{"poussée réussie ?"}
  PO -- non --> RB
  PO -- oui --> M
  O -- non --> M["position = cible"]
  M --> H{"cible = trou ?"}
  H -- oui --> X
  H -- non --> K["check_checkpoint(robot)"] --> RM(["MOVED"])
```

## Algorithme : push

```mermaid
flowchart TD
  A(["push(Q, d)"]) --> S{"Q a un<br/>bouclier ?"}
  S -- oui --> S1["consommer le bouclier"] --> NO(["false : Q reste,<br/>le pousseur s'arrête"])
  S -- non --> N["suivante = Q.position + d"]
  N --> I{"suivante dans<br/>0..11 ?"}
  I -- non --> E["éliminer Q"] --> YES(["true"])
  I -- oui --> W{"suivante = mur ?"}
  W -- oui --> DMG["Q endommagé"] --> NO
  W -- non --> R{"robot R sur<br/>la suivante ?"}
  R -- oui --> RR[["push(R, d)<br/>poussée en chaîne"]]
  RR --> RO{"réussie ?"}
  RO -- non --> NO
  RO -- oui --> MV
  R -- non --> MV["Q.position = suivante<br/>(orientation inchangée)"]
  MV --> H{"suivante = trou ?"}
  H -- oui --> E
  H -- non --> K["check_checkpoint(Q)"] --> YES
```

## Diagramme de séquence : décision de l’IA

```mermaid
sequenceDiagram
  autonumber
  participant G as Game
  participant PS as PerceptronStrategy
  participant SIM as simulate()
  participant RE as RulesEngine (copie)
  participant F as extract()
  participant P as Perceptron

  G->>PS: choose(state, robot, main de 5 cartes, 3)
  PS->>PS: candidats = permutations(main, 3), doublons retirés (≤ 60)
  loop chaque candidat
    PS->>SIM: simulate(state, robot, candidat)
    SIM->>SIM: copie = state.clone()
    SIM->>RE: 3 cartes + tapis roulants sur la copie
    RE-->>SIM: copie après le tour + événements
    SIM-->>PS: SimResult
    PS->>F: extract(state, résultat, distances)
    F-->>PS: x = [progression, CP, éliminé, risque, ...]
    PS->>P: score(x)
    P-->>PS: tanh(w · x + b)
  end
  PS-->>G: le candidat au score maximal
```
