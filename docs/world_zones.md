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
| 11 | Temple Street | 532,399 | 536,568 | "on Temple Street" |
| 12 | Rose Street | 537,551 | 578,555 | "on Rose Street" |
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
| 24 | Crystal Armor Shop | 540,498 | 550,504 | "in the Crystal Armor Shop" |
| 25 | Cloth Armor Shop | 540,507 | 550,517 | "in the Cloth Armor Shop" |
| 26 | Weapon Shop | 540,479 | 553,487 | "in the Weapon Shop" |
| 27 | Tavern of the Blue Ogre | 507,482 | 514,487 | "in the Tavern of the Blue Ogre" |
| 28 | Bank | 515,436 | 522,444 | "in the Bank" |
| 29 | Bank | 493,479 | 503,486 | "in the Bank" |
| 30 | Arena Street | 484,442 | 488,490 | "on Arena Street" |
| 31 | Arena Street | 489,442 | 508,446 | "on Arena Street" |
| 32 | Cirrus' House | 540,442 | 546,451 | "in Cirrus' House" |
| 33 | Gunther's House | 621,440 | 627,446 | "in Gunther's House" |
| 34 | Robin's House | 621,481 | 628,487 | "in Robin's House" |
| 35 | Syleia's House | 607,423 | 613,431 | "in Syleia's House" |
| 36 | Gina's Shop | 483,497 | 490,501 | "in Gina's Shop" |
| 37 | Garna's Shop | 539,411 | 546,417 | "in Garna's Shop" |
| 38 | Manfred's House | 539,424 | 547,431 | "in Manfred's House" |
| 39 | Barracks | 548,411 | 557,422 | "in the Barracks" |
| 40 | Leopold's House | 550,424 | 557,431 | "in Leopold's House" |
| 41 | Serena's House | 521,450 | 528,459 | "in Serena's House" |
| 42 | Magic Maze | 540,456 | 564,474 | "in the Magic Maze" |
| 43 | Steven's House | 520,464 | 529,472 | "in Steven's House" |
| 44 | Golden Armor Shop | 519,477 | 527,484 | "in the Golden Armor Shop" |
| 45 | New Street | 537,434 | 616,438 | "on New Street" |
| 46 | Gordon's House | 559,442 | 565,448 | "in Gordon's House" |
| 47 | Nasir's House | 571,442 | 577,448 | "in Nasir's House" |
| 48 | Templar Outlaws | 582,442 | 610,462 | "at Templar Outlaws" |
| 49 | South End | 614,434 | 618,495 | "on South End" |
| 50 | Skeleton Lord | 590,467 | 610,488 | "at Skeleton Lord" |
| 51 | Merchant's Way | 537,491 | 613,495 | "on Merchant's Way" |
| 52 | Merchant's Way | 464,491 | 531,495 | "on Merchant's Way" |
| 53 | Ingrid's House | 593,498 | 601,505 | "in Ingrid's House" |
| 54 | Abandoned Kwai Clan Hall | 501,400 | 526,432 | "in the Abandoned Kwai Clan Hall" |
| 55 | Abandoned Gorn Clan Hall | 500,558 | 525,590 | "in the Abandoned Gorn Clan Hall" |
| 56 | Arena | 493,448 | 519,476 | "in the Arena" |
| 57 | Black Stronghold | 411,331 | 478,394 | "in the Black Stronghold" |
| 58 | Dungeon of Doors | 561,410 | 604,430 | "in the Dungeon of Doors" |
| 59 | Random Dungeon | 125,57 | 197,131 | "in the Random Dungeon" |
| 60 | Mine, 1st Level | 411,460 | 479,529 | "in the Mine, 1st Level" |
| 61 | Mine, 2nd Level | 771,20 | 839,89 | "in the Mine, 2nd Level" |
| 62 | Mine, 3rd Level | 700,20 | 768,89 | "in the Mine, 3rd Level" |
| 63 | Labyrinth, Grolm Gorge | 52,52 | 105,104 | "in the Labyrinth, Grolm Gorge" |
| 64 | Labyrinth, Lizard Gorge | 58,158 | 154,212 | "in the Labyrinth, Lizard Gorge" |
| 65 | Labyrinth, Spellcaster Gorge | 30,236 | 151,307 | "in the Labyrinth, Spellcaster Gorge" |
| 66 | Labyrinth, Knight Gorge | 25,330 | 110,375 | "in the Labyrinth, Knight Gorge" |
| 67 | Labyrinth, Undead Gorge | 16,385 | 119,455 | "in the Labyrinth, Undead Gorge" |
| 68 | Labyrinth, Undead Gorge | 16,459 | 56,487 | "in the Labyrinth, Undead Gorge" |
| 69 | Labyrinth, Light&Dark Gorge | 16,489 | 81,529 | "in the Labyrinth, Light&Dark Gorge" |
| 70 | Labyrinth, Water Gorge | 16,529 | 81,591 | "in the Labyrinth, Water Gorge" |
| 71 | Labyrinth, Final Entry | 16,593 | 37,602 | "in the Labyrinth, Final Entry" |
| 72 | Labyrinth, Final Preparations | 16,602 | 48,608 | "in the Labyrinth, Final Preparations" |
| 73 | Labyrinth, Final Test | 38,593 | 48,602 | "in the Labyrinth, Final Test" |
| 74 | Labyrinth, Final Reward | 49,593 | 80,608 | "in the Labyrinth, Final Reward" |
| 75 | Labyrinth, Forest Gorge | 15,611 | 126,703 | "in the Labyrinth, Forest Gorge" |
| 76 | Labyrinth, Forest Gorge | 112,703 | 126,708 | "in the Labyrinth, Forest Gorge" |
| 77 | Labyrinth, Riddle Gorge | 15,704 | 66,724 | "in the Labyrinth, Riddle Gorge" |
| 78 | Labyrinth, Riddle Gorge | 15,724 | 48,804 | "in the Labyrinth, Riddle Gorge" |
| 79 | Labyrinth, Riddle Gorge | 15,804 | 37,812 | "in the Labyrinth, Riddle Gorge" |
| 80 | Labyrinth, Sunken Dark | 180,900 | 299,999 | "in the Labyrinth, Sunken Dark" |
| 81 | Entry Hall | 181,936 | 202,962 | "in the Entry Hall" |
| 82 | Atrium | 203,924 | 238,969 | "in the Atrium" |
| 83 | Library | 239,924 | 274,969 | "in the Library" |
| 84 | Crypt | 275,901 | 298,998 | "in the Crypt" |
| 85 | Cistern | 203,970 | 274,998 | "in the Cistern" |
| 86 | Vault | 181,963 | 202,998 | "in the Vault" |
| 87 | Labyrinth, Seasons Gorge | 49,779 | 118,894 | "in the Labyrinth, Seasons Gorge" |
| 88 | Hourglass Chamber | 49,779 | 57,786 | "in the Hourglass Chamber" |
| 89 | Summer | 50,787 | 117,804 | "in Summer" |
| 90 | Summer | 89,805 | 117,847 | "in Summer" |
| 91 | Spring | 50,805 | 88,848 | "in Spring" |
| 92 | Inn | 51,826 | 59,834 | "in the Inn" |
| 93 | Fall | 89,848 | 117,887 | "in Fall" |
| 94 | Fall | 103,888 | 112,894 | "in Fall" |
| 95 | Winter | 50,849 | 88,887 | "in Winter" |
| 96 | Spider Underground | 212,50 | 305,104 | "in the Spider Underground" |
| 97 | Ghost Underground | 210,120 | 270,162 | "in the Ghost Underground" |
| 98 | Pentagram Quest | 210,300 | 410,600 | "in the Pentagram Quest" |
| 99 | Ice Pentagram Quest | 368,246 | 408,299 | "in the Ice Pentagram Quest" |
| 100 | Ice Pentagram Quest | 330,264 | 367,299 | "in the Ice Pentagram Quest" |
| 101 | Underwater Pentagram Quest | 265,225 | 367,263 | "in the Underwater Pentagram Quest" |
| 102 | Underwater Pentagram Quest | 265,264 | 329,293 | "in the Underwater Pentagram Quest" |
| 103 | Underwater Pentagram Quest | 265,294 | 320,300 | "in the Underwater Pentagram Quest" |
| 104 | Underground II | 822,176 | 1020,333 | "in the Underground II" |
| 105 | Elysium | 792,796 | 813,811 | "in the Elysium" |
| 106 | Gargoyle's Nest | 367,227 | 410,244 | "in the Gargoyle's Nest" |
| 107 | Gargoyle's Nest | 410,227 | 480,329 | "in the Gargoyle's Nest" |
| 108 | Aston | 1,1 | 20,20 | "in Aston" |
| 109 | Astonian Inn | 622,466 | 629,477 | "in the Astonian Inn" |
| 110 | Astonian Inn | 630,466 | 633,481 | "in the Astonian Inn" |
| 111 | Astonian Inn | 61,122 | 65,131 | "in the Astonian Inn" |
| 112 | Astonian Inn | 53,118 | 60,124 | "in the Astonian Inn" |
| 113 | Astonian Inn | 36,106 | 52,141 | "in the Astonian Inn" |
| 114 | Astonian Inn | 29,137 | 38,144 | "in the Astonian Inn" |
| 115 | Memorial Park | 578,566 | 633,596 | "in the Memorial Park" |
| 116 | Staffers Corner | 820,158 | 851,161 | "in the Staffers Corner" |
| 117 | Staffers Corner | 807,151 | 819,168 | "in the Staffers Corner" |
| 118 | Staffers Corner | 793,146 | 805,156 | "in the Staffers Corner" |
| 119 | Staffers Corner | 799,158 | 805,168 | "in the Staffers Corner" |
| 120 | Staffers Corner | 794,163 | 798,165 | "in the Staffers Corner" |
| 121 | Tower I | 632,240 | 647,257 | "in the Tower I" |
| 122 | Tower II | 822,337 | 837,352 | "in the Tower II" |
| 123 | Tower III | 824,360 | 839,373 | "in the Tower III" |
| 124 | Tower IV | 823,380 | 838,395 | "in the Tower IV" |
| 125 | Tower V | 822,401 | 837,416 | "in the Tower V" |
| 126 | Tower VI | 822,420 | 838,435 | "in the Tower VI" |
| 127 | Tower VII | 844,337 | 860,350 | "in the Tower VII" |
| 128 | Tower VIII | 844,354 | 860,368 | "in the Tower VIII" |
| 129 | Tower IX | 845,374 | 861,389 | "in the Tower IX" |
| 130 | Tower X | 844,395 | 860,411 | "in the Tower X" |
| 131 | Tower XI | 844,415 | 860,430 | "in the Tower XI" |
| 132 | Tower XII | 867,337 | 885,356 | "in the Tower XII" |
| 133 | Tower XIII | 865,361 | 882,376 | "in the Tower XIII" |
| 134 | Tower XIV | 865,380 | 883,396 | "in the Tower XIV" |
| 135 | Tower XV | 870,400 | 886,424 | "in the Tower XV" |
| 136 | Tower XV | 865,416 | 869,424 | "in the Tower XV" |
| 137 | Tower XVI | 892,337 | 916,359 | "in the Tower XVI" |
| 138 | Tower XVI | 892,360 | 908,378 | "in the Tower XVI" |
| 139 | Tower XVII | 892,386 | 911,406 | "in the Tower XVII" |
| 140 | Tower XVIII | 890,410 | 909,429 | "in the Tower XVIII" |
| 141 | Tower XIX | 921,337 | 940,356 | "in the Tower XIX" |
| 142 | Tower XX | 926,360 | 940,378 | "in the Tower XX" |
| 143 | Tower XX | 924,379 | 942,404 | "in the Tower XX" |
| 144 | Tower XX | 921,405 | 945,415 | "in the Tower XX" |
| 145 | Pentagram Quest | 411,436 | 476,456 | "in the Pentagram Quest" |
| 146 | Aston Hall | 597,600 | 619,619 | "in Aston Hall" |
| 147 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 148 | Ice Pents Shrine | 321,294 | 327,300 | "in the Ice Pents Shrine" |
| 149 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 150 | Aston Hall | 577,597 | 596,628 | "in the Aston Hall" |
| 151 | Aston Hall | 597,620 | 619,628 | "in the Aston Hall" |
| 152 | Aston Hall | 620,597 | 633,628 | "in the Aston Hall" |
| 153 | Aston Hall | 597,597 | 619,599 | "in the Aston Hall" |
| 154 | Underground I | 836,151 | 846,154 | "in the Underground I" |
| 155 | Black Stronghold | 479,360 | 479,363 | "in the Black Stronghold" |
| 156 | Astonian Inn | 634,466 | 639,477 | "in the Astonian Inn" |
| 157 | Aston | 532,406 | 536,406 | "in Aston" |
| 158 | Pentagram Quest | 469,457 | 473,459 | "in the Pentagram Quest" |
