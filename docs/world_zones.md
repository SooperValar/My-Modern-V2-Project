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
| 67 | Pentagram Quest | 210,300 | 410,600 | "in the Pentagram Quest" |
| 68 | Ice Pentagram Quest | 330,246 | 408,299 | "in the Ice Pentagram Quest" |
| 69 | Underground II | 822,176 | 1020,333 | "in the Underground II" |
| 70 | Elysium | 792,796 | 813,811 | "in the Elysium" |
| 71 | Gargoyle's Nest | 367,227 | 410,244 | "in the Gargoyle's Nest" |
| 72 | Gargoyle's Nest | 410,227 | 480,329 | "in the Gargoyle's Nest" |
| 73 | Aston | 1,1 | 20,20 | "in Aston" |
| 74 | Astonian Inn | 622,466 | 629,477 | "in the Astonian Inn" |
| 75 | Astonian Inn | 630,466 | 633,481 | "in the Astonian Inn" |
| 76 | Astonian Inn | 61,122 | 65,131 | "in the Astonian Inn" |
| 77 | Astonian Inn | 53,118 | 60,124 | "in the Astonian Inn" |
| 78 | Astonian Inn | 36,106 | 52,141 | "in the Astonian Inn" |
| 79 | Astonian Inn | 29,137 | 38,144 | "in the Astonian Inn" |
| 80 | Memorial Park | 578,566 | 633,596 | "in the Memorial Park" |
| 81 | Staffers Corner | 820,158 | 851,161 | "in the Staffers Corner" |
| 82 | Staffers Corner | 807,151 | 819,168 | "in the Staffers Corner" |
| 83 | Staffers Corner | 793,146 | 805,156 | "in the Staffers Corner" |
| 84 | Staffers Corner | 799,158 | 805,168 | "in the Staffers Corner" |
| 85 | Staffers Corner | 794,163 | 798,165 | "in the Staffers Corner" |
| 86 | Tower I | 632,240 | 647,257 | "in the Tower I" |
| 87 | Tower II | 822,337 | 837,352 | "in the Tower II" |
| 88 | Tower III | 822,354 | 837,367 | "in the Tower III" |
| 89 | Tower IV | 822,369 | 837,384 | "in the Tower IV" |
| 90 | Tower V | 822,386 | 837,401 | "in the Tower V" |
| 91 | Tower VI | 854,338 | 870,353 | "in the Tower VI" |
| 92 | Tower VII | 854,355 | 870,368 | "in the Tower VII" |
| 93 | Tower VIII | 854,370 | 870,384 | "in the Tower VIII" |
| 94 | Tower IX | 854,386 | 870,401 | "in the Tower IX" |
| 95 | Tower X | 854,403 | 870,419 | "in the Tower X" |
| 96 | Tower XI | 854,422 | 870,437 | "in the Tower XI" |
| 97 | Tower XII | 851,440 | 869,459 | "in the Tower XII" |
| 98 | Tower XIII | 849,463 | 866,478 | "in the Tower XIII" |
| 99 | Tower XIV | 848,479 | 866,495 | "in the Tower XIV" |
| 100 | Tower XV | 847,498 | 863,522 | "in the Tower XV" |
| 101 | Tower XV | 842,514 | 846,522 | "in the Tower XV" |
| 102 | Tower XVI | 839,523 | 863,545 | "in the Tower XVI" |
| 103 | Tower XVI | 839,546 | 855,564 | "in the Tower XVI" |
| 104 | Tower XVII | 839,570 | 858,590 | "in the Tower XVII" |
| 105 | Tower XVIII | 839,594 | 858,613 | "in the Tower XVIII" |
| 106 | Tower XIX | 839,616 | 858,635 | "in the Tower XIX" |
| 107 | Tower XX | 841,639 | 855,657 | "in the Tower XX" |
| 108 | Tower XX | 839,658 | 857,683 | "in the Tower XX" |
| 109 | Tower XX | 836,684 | 860,694 | "in the Tower XX" |
| 110 | Pentagram Quest | 411,436 | 476,456 | "in the Pentagram Quest" |
| 111 | Aston Hall | 597,600 | 619,619 | "in Aston Hall" |
| 112 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 113 | Ice Pents Shrine | 321,294 | 327,300 | "in the Ice Pents Shrine" |
| 114 | Lizard Temple Shrine | 529,198 | 537,204 | "in the Lizard Temple Shrine" |
| 115 | Aston Hall | 577,597 | 596,628 | "in the Aston Hall" |
| 116 | Aston Hall | 597,620 | 619,628 | "in the Aston Hall" |
| 117 | Aston Hall | 620,597 | 633,628 | "in the Aston Hall" |
| 118 | Aston Hall | 597,597 | 619,599 | "in the Aston Hall" |
| 119 | Underground I | 836,151 | 846,154 | "in the Underground I" |
| 120 | Black Stronghold | 479,360 | 479,363 | "in the Black Stronghold" |
| 121 | Astonian Inn | 634,466 | 639,477 | "in the Astonian Inn" |
| 122 | Aston | 532,406 | 536,406 | "in Aston" |
| 123 | Pentagram Quest | 469,457 | 473,459 | "in the Pentagram Quest" |
