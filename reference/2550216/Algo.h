#ifndef ALGO_H
#define ALGO_H

#include "PathNode.h"
#include <iostream>
#include <fstream>
#include <string>
#include <cmath>
#include <vector>
#include <algorithm>

using namespace std;

// Task 1 — Degrees of Separation in a Social Network:
PathNode *findSocialPath(double adjMatrix[100][100], int startPerson, int goalPerson);
// Task 2 — Drone Delivery in 2D Space with Three Heuristics:
PathNode *findDronePath(double weightMatrix[100][100], int coords[100][2],
                        int startPoint, int goalPoint, int mode);
// Task 3 — Warehouse Robot Navigation with Obstacles
PathNode *findWarehousePath(int warehouse[100][100], int m, int n, int startX,
                            int startY, int goalX, int goalY, int mode);
// Task 4 — Evacuation Route Planning:
PathNode *findEvacuationPath(int floorPlan[100][100], int m, int n, int startX,
                             int startY, int exitX, int exitY, double weightMatrix[100][100], int mode);
#endif
