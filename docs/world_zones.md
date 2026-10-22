# Zones

Zone names come from the `area[]` table in `server/area.c`: rectangles of map x1,y1 - x2,y2.
Shown by `/who`, by NPCs when asked where you are, and in server logs. A spot inside several rectangles shows every matching name, in table order.

![zones](world_zones.png)

| # | Name | x1,y1 | x2,y2 | Says |
|---|---|---|---|---|
| 0 | Aston | 481,407 | 633,596 | "in Aston" |
| 1 | Lizard Temple | 497,205 | 537,233 | "in the Lizard Temple" |
| 2 | Strange Forest | 480,234 | 634,405 | "in the Strange Forest" |
| 3 | Underground I | 840,0 | 1024,157 | "in Underground I" |
| 4 | Temple of Skua | 491,504 | 520,520 | "in the Temple of Skua" |
| 5 | Leather Armor Shop | 520,524 | 529,534 | "in the Leather Armor Shop" |
| 6 | Jamil's House | 539,525 | 548,532 | "in Jamil's House" |
| 7 | Temple of the Purple One | 545,536 | 564,548 | "in the Temple of the Purple One" |
| 8 | Thieves House I | 499,539 | 528,550 | "in the Thieves House I" |
| 9 | Thieves Basement | 20,20 | 49,69 | "in the Thieves Basement" |
| 10 | Thieves House II | 499,525 | 514,538 | "in the Thieves House II" |
| 11 | Temple Street | 532,439 | 536,550 | "on Temple Street" |
| 12 | Rose Street | 532,551 | 578,555 | "on Rose Street" |
| 13 | Cursed Tomb | 538,559 | 575,588 | "in the Cursed Tomb" |
| 14 | Castle Way | 574,496 | 578,550 | "on Castle Way" |
| 15 | Haunted Castle | 588,530 | 623,554 | "in the Haunted Castle" |
| 16 | Inga's House | 562,525 | 570,531 | "in Inga's House" |
| 17 | Jefferson's House | 582,519 | 587,524 | "in Jefferson's House" |
| 18 | Steel Armor Shop | 582,510 | 591,514 | "in the Steel Armor Shop" |
| 19 | Joe's House | 554,509 | 570,520 | "in Joe's House" |
| 20 | Bronze Armor Shop | 582,498 | 588,505 | "in the Bronze Armor Shop" |
| 21 | Damor's Magic Shop | 569,468 | 582,487 | "in Damor's Magic Shop" |
| 22 | Brunhild's Shop | 558,481 | 567,487 | "in Brunhild's Shop" |
| 23 | Sirjan's House | 555,499 | 563,504 | "in Sirjan's House" |
| 24 | Cloth Armor Shop | 541,499 | 549,503 | "in the Cloth Armor Shop" |
| 25 | Weapon Shop | 540,479 | 553,487 | "in the Weapon Shop" |
| 26 | Tavern of the Blue Ogre | 507,482 | 514,487 | "in the Tavern of the Blue Ogre" |
| 27 | Bank | 515,436 | 522,444 | "in the Bank" |
| 28 | Cirrus' House | 540,442 | 546,451 | "in Cirrus' House" |
| 29 | Serena's House | 521,450 | 528,459 | "in Serena's House" |
| 30 | Magic Maze | 540,456 | 564,474 | "in the Magic Maze" |
| 31 | Steven's House | 512,465 | 528,471 | "in Steven's House" |
| 32 | Golden Armor Shop | 519,477 | 527,484 | "in the Golden Armor Shop" |
| 33 | New Street | 537,434 | 616,438 | "on New Street" |
| 34 | Gordon's House | 559,442 | 565,448 | "in Gordon's House" |
| 35 | Nasir's House | 571,442 | 577,448 | "in Nasir's House" |
| 36 | Templar Outlaws | 582,442 | 610,462 | "at Templar Outlaws" |
| 37 | South End | 614,434 | 618,495 | "on South End" |
| 38 | Skeleton Lord | 590,467 | 610,488 | "at Skeleton Lord" |
| 39 | Merchant's Way | 537,491 | 613,495 | "on Merchant's Way" |
| 40 | Ingrid's House | 593,498 | 601,505 | "in Ingrid's House" |
| 41 | Abandoned Kwai Clan Hall | 501,400 | 526,432 | "in the Abandoned Kwai Clan Hall" |
| 42 | Abandoned Gorn Clan Hall | 500,558 | 525,590 | "in the Abandoned Gorn Clan Hall" |
| 43 | Arena | 493,448 | 519,476 | "in the Arena" |
| 44 | Black Stronghold | 411,331 | 478,394 | "in the Black Stronghold" |
| 45 | Dungeon of Doors | 561,410 | 604,430 | "in the Dungeon of Doors" |
| 46 | Random Dungeon | 125,57 | 197,131 | "in the Random Dungeon" |
| 47 | Mine, 1st Level | 411,460 | 479,529 | "in the Mine, 1st Level" |
| 48 | Mine, 2nd Level | 771,20 | 839,89 | "in the Mine, 2nd Level" |
| 49 | Mine, 3rd Level | 700,20 | 768,89 | "in the Mine, 3rd Level" |
| 50 | Labyrinth, Grolm Gorge | 52,52 | 105,104 | "in the Labyrinth, Grolm Gorge" |
| 51 | Labyrinth, Lizard Gorge | 58,158 | 154,212 | "in the Labyrinth, Lizard Gorge" |
| 52 | Labyrinth, Spellcaster Gorge | 30,236 | 151,307 | "in the Labyrinth, Spellcaster Gorge" |
| 53 | Labyrinth, Knight Gorge | 25,330 | 110,375 | "in the Labyrinth, Knight Gorge" |
| 54 | Labyrinth, Undead Gorge | 16,385 | 119,455 | "in the Labyrinth, Undead Gorge" |
| 55 | Labyrinth, Undead Gorge | 16,459 | 56,487 | "in the Labyrinth, Undead Gorge" |
| 56 | Labyrinth, Light&Dark Gorge | 16,489 | 81,529 | "in the Labyrinth, Light&Dark Gorge" |
| 57 | Labyrinth, Water Gorge | 16,529 | 81,591 | "in the Labyrinth, Water Gorge" |
| 58 | Labyrinth, Final Entry | 16,593 | 37,602 | "in the Labyrinth, Final Entry" |
| 59 | Labyrinth, Final Preparations | 16,602 | 48,608 | "in the Labyrinth, Final Preparations" |
| 60 | Labyrinth, Final Test | 38,593 | 48,602 | "in the Labyrinth, Final Test" |
| 61 | Labyrinth, Final Reward | 49,593 | 80,608 | "in the Labyrinth, Final Reward" |
| 62 | Labyrinth, Forest Gorge | 15,611 | 126,703 | "in the Labyrinth, Forest Gorge" |
| 63 | Labyrinth, Forest Gorge | 112,703 | 126,708 | "in the Labyrinth, Forest Gorge" |
| 64 | Labyrinth, Riddle Gorge | 15,704 | 66,724 | "in the Labyrinth, Riddle Gorge" |
| 65 | Labyrinth, Riddle Gorge | 15,724 | 48,804 | "in the Labyrinth, Riddle Gorge" |
| 66 | Labyrinth, Riddle Gorge | 15,804 | 37,812 | "in the Labyrinth, Riddle Gorge" |
| 67 | Labyrinth, Sunken Dark | 180,900 | 299,999 | "in the Labyrinth, Sunken Dark" |
| 68 | Entry Hall | 181,936 | 202,962 | "in the Entry Hall" |
| 69 | Atrium | 203,924 | 238,969 | "in the Atrium" |
| 70 | Library | 239,924 | 274,969 | "in the Library" |
| 71 | Crypt | 275,901 | 298,998 | "in the Crypt" |
| 72 | Cistern | 203,970 | 274,998 | "in the Cistern" |
| 73 | Vault | 181,963 | 202,998 | "in the Vault" |
| 74 | Labyrinth, Seasons Gorge | 49,779 | 118,894 | "in the Labyrinth, Seasons Gorge" |
| 75 | Hourglass Chamber | 49,779 | 57,786 | "in the Hourglass Chamber" |
| 76 | Summer | 50,787 | 117,804 | "in Summer" |
| 77 | Summer | 89,805 | 117,847 | "in Summer" |
| 78 | Spring | 50,805 | 88,848 | "in Spring" |
| 79 | Inn | 51,826 | 59,834 | "in the Inn" |
| 80 | Fall | 89,848 | 117,887 | "in Fall" |
| 81 | Fall | 103,888 | 112,894 | "in Fall" |
| 82 | Winter | 50,849 | 88,887 | "in Winter" |
| 83 | Spider Underground | 212,50 | 305,104 | "in the Spider Underground" |
| 84 | Ghost Underground | 210,120 | 270,162 | "in the Ghost Underground" |
| 85 | Pentagram Quest | 210,300 | 410,600 | "in the Pentagram Quest" |
| 86 | Ice Pentagram Quest | 368,246 | 408,299 | "in the Ice Pentagram Quest" |
| 87 | Ice Pentagram Quest | 330,264 | 367,299 | "in the Ice Pentagram Quest" |
| 88 | Underwater Pentagram Quest | 265,225 | 367,263 | "in the Underwater Pentagram Quest" |
| 89 | Underwater Pentagram Quest | 265,264 | 329,293 | "in the Underwater Pentagram Quest" |
| 90 | Underwater Pentagram Quest | 265,294 | 320,300 | "in the Underwater Pentagram Quest" |
| 91 | Underground II | 822,176 | 1020,333 | "in the Underground II" |
| 92 | Elysium | 792,796 | 813,811 | "in the Elysium" |
| 93 | Gargoyle's Nest | 367,227 | 410,244 | "in the Gargoyle's Nest" |
| 94 | Gargoyle's Nest | 410,227 | 480,329 | "in the Gargoyle's Nest" |
| 95 | Aston | 1,1 | 20,20 | "in Aston" |
| 96 | Astonian Inn | 622,466 | 629,477 | "in the Astonian Inn" |
| 97 | Astonian Inn | 630,466 | 633,481 | "in the Astonian Inn" |
| 98 | Astonian Inn | 61,122 | 65,131 | "in the Astonian Inn" |
| 99 | Astonian Inn | 53,118 | 60,124 | "in the Astonian Inn" |
| 100 | Astonian Inn | 36,106 | 52,141 | "in the Astonian Inn" |
| 101 | Astonian Inn | 29,137 | 38,144 | "in the Astonian Inn" |
| 102 | Memorial Park | 578,566 | 633,596 | "in the Memorial Park" |
| 103 | Staffers Corner | 820,158 | 851,161 | "in the Staffers Corner" |
| 104 | Staffers Corner | 807,151 | 819,168 | "in the Staffers Corner" |
| 105 | Staffers Corner | 793,146 | 805,156 | "in the Staffers Corner" |
| 106 | Staffers Corner | 799,158 | 805,168 | "in the Staffers Corner" |
| 107 | Staffers Corner | 794,163 | 798,165 | "in the Staffers Corner" |
| 108 | Tower I | 632,240 | 647,257 | "in the Tower I" |
| 109 | Tower II | 822,337 | 837,352 | "in the Tower II" |
| 110 | Tower III | 824,360 | 839,373 | "in the Tower III" |
| 111 | Tower IV | 823,380 | 838,395 | "in the Tower IV" |
| 112 | Tower V | 822,401 | 837,416 | "in the Tower V" |
| 113 | Tower VI | 822,420 | 838,435 | "in the Tower VI" |
| 114 | Tower VII | 844,337 | 860,350 | "in the Tower VII" |
| 115 | Tower VIII | 844,354 | 860,368 | "in the Tower VIII" |
| 116 | Tower IX | 845,374 | 861,389 | "in the Tower IX" |
| 117 | Tower X | 844,395 | 860,411 | "in the Tower X" |
| 118 | Tower XI | 844,415 | 860,430 | "in the Tower XI" |
| 119 | Tower XII | 867,337 | 885,356 | "in the Tower XII" |
| 120 | Tower XIII | 865,361 | 882,376 | "in the Tower XIII" |
| 121 | Tower XIV | 865,380 | 883,396 | "in the Tower XIV" |
| 122 | Tower XV | 870,400 | 886,424 | "in the Tower XV" |
| 123 | Tower XV | 865,416 | 869,424 | "in the Tower XV" |
| 124 | Tower XVI | 892,337 | 916,359 | "in the Tower XVI" |
| 125 | Tower XVI | 892,360 | 908,378 | "in the Tower XVI" |
| 126 | Tower XVII | 892,386 | 911,406 | "in the Tower XVII" |
| 127 | Tower XVIII | 890,410 | 909,429 | "in the Tower XVIII" |
| 128 | Tower XIX | 921,337 | 940,356 | "in the Tower XIX" |
| 129 | Tower XX | 926,360 | 940,378 | "in the Tower XX" |
| 130 | Tower XX | 924,379 | 942,404 | "in the Tower XX" |
| 131 | Tower XX | 921,405 | 945,415 | "in the Tower XX" |
| 132 | Pentagram Quest | 411,436 | 476,456 | "in the Pentagram Quest" |
| 133 | Aston Hall | 597,600 | 619,619 | "in Aston Hall" |
| 134 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 135 | Ice Pents Shrine | 321,294 | 327,300 | "in the Ice Pents Shrine" |
| 136 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 137 | Aston Hall | 577,597 | 596,628 | "in the Aston Hall" |
| 138 | Aston Hall | 597,620 | 619,628 | "in the Aston Hall" |
| 139 | Aston Hall | 620,597 | 633,628 | "in the Aston Hall" |
| 140 | Aston Hall | 597,597 | 619,599 | "in the Aston Hall" |
| 141 | Underground I | 836,151 | 846,154 | "in the Underground I" |
| 142 | Black Stronghold | 479,360 | 479,363 | "in the Black Stronghold" |
| 143 | Astonian Inn | 634,466 | 639,477 | "in the Astonian Inn" |
| 144 | Aston | 532,406 | 536,406 | "in Aston" |
| 145 | Pentagram Quest | 469,457 | 473,459 | "in the Pentagram Quest" |
