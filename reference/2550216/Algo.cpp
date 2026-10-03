#include "Algo.h"

// Task 1 — Degrees of Separation in a Social Network:

void computeHeuristic(double adjMatrix[100][100], int goalPerson, double h[100]) {
    bool visited[100];

    for (int i = 0; i < 100; i++) {
        h[i] = 1e9;
        visited[i] = false;
    }

    vector <int> q;
    int ptr = 0;

    h[goalPerson] = 0;
    visited[goalPerson] = true;
    q.push_back(goalPerson);

    while (ptr < q.size()) {
        int current = q[ptr];
        ptr++;
        for (int i = 0; i < 100; i++) {
            if (adjMatrix[i][current] != 0 && visited[i] == false) {
                visited[i] = true;
                h[i] = h[current] + 1;
                q.push_back(i);
            }
        }
    }
}

PathNode *buildSocialPath(int parent[100], double g[100], double h[100],
                          double f[100], int startPerson, int goalPerson)
{
    PathNode *head = NULL;
    int current = goalPerson;

    while (current != -1) {
        PathNode* node = new PathNode;
        node->name = to_string(current);
        node->f = f[current];
        node->g = g[current];
        node->h = h[current];
        node->next = head;
        head = node;
        
        if (current == startPerson) break;
        current = parent[current];
    }
    return head;
}
PathNode *findSocialPath(double adjMatrix[100][100], int startPerson, int goalPerson)
{
    const double INF = 1e9;
    double g[100];
    double h[100];
    double f[100];
    int parent[100];
    bool processed[100];
    bool inQueue[100];

    vector<int> queue;

    computeHeuristic(adjMatrix, goalPerson, h);

    for (int i = 0; i < 100; i++) {
        g[i] = INF;
        f[i] = INF;
        parent[i] = -1;
        processed[i] = false;
        inQueue[i] = false;
    }

    g[startPerson] = 0;
    f[startPerson] = g[startPerson] + h[startPerson];
    queue.push_back(startPerson);
    inQueue[startPerson] = true;

    while(!queue.empty()) {

        int bestIdx = 0;
        for (int i = 0; i < queue.size(); i++) {
            int currentNode = queue[i];
            int best = queue[bestIdx];

            if (f[currentNode] < f[best]) bestIdx = i;
            else if ((f[currentNode] == f[best]) && (h[currentNode] < h[best])) bestIdx = i;
        }

        int current = queue[bestIdx];
        queue.erase(queue.begin() + bestIdx);
        inQueue[current] = false;

        if (current == goalPerson) return buildSocialPath(parent, g, h, f, startPerson, goalPerson);
        processed[current] = true;

        for (int i = 0; i < 100; i++) {
            if (adjMatrix[current][i] == 0) continue;
            if (processed[i]) continue;
            double newCost = g[current] + 1;
            if (newCost < g[i]) {
                g[i] = newCost;
                f[i] = g[i] + h[i];
                parent[i] = current;
                if (!inQueue[i]) {
                    queue.push_back(i);
                    inQueue[i] = true;
                }
            }
        }
    }
    return NULL;
}

// Task 2 — Drone Delivery in 2D Space with Three Heuristics:

double droneHeuristic(int coords[100][2], int current, int goal, int mode)
{
    double deltaX = abs(coords[current][0] - coords[goal][0]);
    double deltaY = abs(coords[current][1] - coords[goal][1]);

    if (mode == 1)
    {
        return deltaX + deltaY;
    }
    else if (mode == 2)
    {
        return sqrt(deltaX * deltaX + deltaY * deltaY);
    }
    else if (mode == 3)
    {
        return max(deltaX, deltaY);
    }

    return 0;
}

PathNode *buildDronePath(int parent[100], double g[100], double h[100], double f[100], 
                        int coords[100][2], int startPoint, int goalPoint) 
{
    PathNode *head = NULL;
    int current = goalPoint;

    while (current != -1) {
        PathNode* node = new PathNode;
        node->name = "(" + to_string(coords[current][0]) + "," + to_string(coords[current][1]) + ")";
        node->f = f[current];
        node->g = g[current];
        node->h = h[current];
        node->next = head;
        head = node;
        
        if (current == startPoint) break;
        current = parent[current];
    }
    return head;
}
PathNode *findDronePath(double weightMatrix[100][100], int coords[100][2],
                        int startPoint, int goalPoint, int mode)
{
    const double INF = 1e9;
    double g[100];
    double h[100];
    double f[100];
    bool inQueue[100];
    bool processed[100];
    int parent[100];

    for (int i = 0; i < 100; i++) {
        g[i] = INF;
        f[i] = INF;
        parent[i] = -1;
        inQueue[i] = false;
        processed[i] = false;
    }

    for (int i = 0; i < 100; i++) {
        h[i] = droneHeuristic(coords, i, goalPoint, mode);
    }

    g[startPoint] = 0;
    f[startPoint] = g[startPoint] + h[startPoint];
    vector<int> queue;
    queue.push_back(startPoint);
    inQueue[startPoint] = true;

    while(!queue.empty()) {
        
        int bestIdx = 0;
        for (int i = 0; i < queue.size(); i++) {
            int currentNode = queue[i];
            int bestNode = queue[bestIdx];
            if (f[currentNode] < f[bestNode]) bestIdx = i;
            else if ((f[currentNode] == f[bestNode]) && (h[currentNode] < h[bestNode])) bestIdx = i;
        }

        int current = queue[bestIdx];
        queue.erase(queue.begin() + bestIdx);
        inQueue[current] = false;

        if (current == goalPoint) return buildDronePath(parent, g, h, f, coords, startPoint, goalPoint);
        
        processed[current] = true;

        for (int i = 0; i < 100; i++) {
            if (weightMatrix[current][i] == 0) continue;
            if (processed[i] == true) continue;
            double newCost = g[current] + weightMatrix[current][i];

            if (newCost < g[i]) {
                g[i] = newCost;
                f[i] = g[i] + h[i];
                parent[i] = current;
                if (!inQueue[i]) {
                    queue.push_back(i);
                    inQueue[i] = true;
                }
            } 
        }

    }
    return NULL;
}

// Task 3 — Warehouse Robot Navigation with Obstacles
double warehouseHeuristic(int x, int y, int goalX, int goalY, int mode)
{
    double dx = abs(x - goalX);
    double dy = abs(y - goalY);

    if (mode == 1)
    {
        return dx + dy;
    }
    else if (mode == 2)
    {
        return max(dx, dy);
    }

    return 0;
}

struct Cell
{
    int x;
    int y;
};

PathNode *buildWarehousePath(int parentX[100][100], int parentY[100][100], string moveName[100][100], double g[100][100], 
                            double h[100][100], double f[100][100], int startX, int startY, int goalX, int goalY) {
    
    PathNode *head = NULL;
    int currX = goalX;
    int currY = goalY;
    
    while (currX != startX || currY != startY) {
        PathNode *node = new PathNode;
        
        node->name = moveName[currX][currY];
        node->g = g[currX][currY];
        node->h = h[currX][currY];
        node->f = f[currX][currY];

        node->next = head;
        head = node;

        int prevX = parentX[currX][currY];
        int prevY = parentY[currX][currY];

        currX = prevX;
        currY = prevY;
    }

    return head;
}
PathNode *findWarehousePath(int warehouse[100][100], int m, int n, int startX,
                            int startY, int goalX, int goalY, int mode)
{
    const double INF = 1e9;
    double g[100][100];
    double h[100][100];
    double f[100][100];
    bool processed[100][100];
    bool inQueue[100][100];
    int parentX[100][100];
    int parentY[100][100];
    string move[100][100];

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            g[i][j] = INF;
            h[i][j] = warehouseHeuristic(i, j, goalX, goalY, mode);
            f[i][j] = INF;
            processed[i][j] = false;
            inQueue[i][j] = false;
            parentX[i][j] = -1;
            parentY[i][j] = -1;
            move[i][j] = "";

        }
    }

    int dirX[8] = {-1, 1, 0, 0, -1, -1, 1, 1};
    int dirY[8] = {0, 0, -1, 1, -1, 1, -1, 1};
    string dirName[8] = {"Up", "Down", "Left", "Right", "Up-Left", 
                        "Up-Right", "Down-Left", "Down-Right"};

    vector<Cell> queue;
    queue.push_back({startX, startY});
    g[startX][startY] = 0;
    f[startX][startY] = g[startX][startY] + h[startX][startY];
    inQueue[startX][startY] = true;

    while (!queue.empty()) {
        int bestIdx = 0;
        for (int i = 0; i < queue.size(); i++) {
            int ax = queue[i].x;
            int ay = queue[i].y;
            int bx = queue[bestIdx].x;
            int by = queue[bestIdx].y;

            if (f[ax][ay] < f[bx][by]) bestIdx = i;
            else if (f[ax][ay] == f[bx][by] && h[ax][ay] < h[bx][by]) bestIdx = i;
        } 

        Cell current = queue[bestIdx];
        queue.erase(queue.begin() + bestIdx);
        inQueue[current.x][current.y] = false;
        if ((current.x == goalX) && (current.y == goalY)) return buildWarehousePath(parentX, parentY, move, g, h, f, startX, startY, goalX, goalY);

        processed[current.x][current.y] = true;

        for (int i = 0; i < 8; i++) {
            int nextX = current.x + dirX[i];
            int nextY = current.y + dirY[i];
            double moveCost = 0;

            if (nextX < 0 || nextX >= m) continue;
            if (nextY < 0 || nextY >= n) continue;
            if (warehouse[nextX][nextY] == 1) continue;
            if (processed[nextX][nextY] == true) continue;
            if (dirX[i] != 0 && dirY[i] != 0) {
                moveCost = 1.5;
            } else moveCost = 1;

            double newCost = g[current.x][current.y] + moveCost;
            if (newCost < g[nextX][nextY]) {
                g[nextX][nextY] = newCost;
                f[nextX][nextY] = g[nextX][nextY] + h[nextX][nextY];
                parentX[nextX][nextY] = current.x;
                parentY[nextX][nextY] = current.y;
                move[nextX][nextY] = dirName[i];

                if (!inQueue[nextX][nextY]) {
                    queue.push_back({nextX, nextY});
                    inQueue[nextX][nextY] = true;
                }
            }
        }
    }

    return NULL;
}

// Task 4 — Evacuation Route Planning:

double evacuationHeuristic(int x, int y, int goalX, int goalY, int mode)
{
    double dx = abs(x - goalX);
    double dy = abs(y - goalY);

    if (mode == 1)
    {
        return dx + dy;
    }
    else if (mode == 2)
    {
        return max(dx, dy);
    }

    return 0;
}

PathNode *buildEvacuationPath(int parent[100], double g[100], double h[100],
                              double f[100], int startId, int exitId, int n)
{
    PathNode *head = NULL;
    int current = exitId;

    while (current != -1) {
        PathNode *node = new PathNode;

        int x = current / n;
        int y = current % n;
        node->name = "(" + to_string(x) + ", " + to_string(y) + ")";
        node->g = g[current];
        node->h = h[current];
        node->f = f[current];

        node->next = head;
        head = node;

        if (current == startId) break;
        current = parent[current];
    }

    return head;
}
PathNode *findEvacuationPath(int floorPlan[100][100], int m, int n, int startX,
                             int startY, int exitX, int exitY, double weightMatrix[100][100], int mode)
{

    for (int i = 0; i < 100; i++) {
        for (int j = 0; j < 100; j++) {
            weightMatrix[i][j] = 0;
        }
    }

    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            if (floorPlan[i][j] == 1) continue;

            int source = i * n + j;
            int dirX[8] = {-1, 1, 0, 0, -1, -1, 1, 1};
            int dirY[8] = {0, 0, -1, 1, -1, 1, -1, 1};

            for (int k = 0; k < 8; k++) {
                int nextX = i + dirX[k];
                int nextY = j + dirY[k];

                if (nextX < 0 || nextX >= m) continue;
                if (nextY < 0 || nextY >= n) continue;
                if (floorPlan[nextX][nextY] == 1) continue;

                int target = nextX * n + nextY;
                double cost = 0;
                if (dirX[k] != 0 && dirY[k] != 0) cost = 1.5;
                else cost = 1;
                weightMatrix[source][target] = cost;
            }
        }
    }

    int totalNodes = m * n;
    int startIdx = startX * n + startY;
    int exitIdx = exitX * n + exitY;

    const double INF = 1e9;

    double g[100];
    double h[100];
    double f[100];
    int parent[100];
    bool processed[100];
    bool inQueue[100];

    vector<int> queue;
    for (int i = 0; i < totalNodes; i++) {
        g[i] = INF;
        h[i] = INF;
        f[i] = INF;
        parent[i] = -1;
        processed[i] = false;
        inQueue[i] = false;

        int x = i / n;
        int y = i % n;

        h[i] = evacuationHeuristic(x, y, exitX, exitY, mode); 
    }

    g[startIdx] = 0;
    f[startIdx] = g[startIdx] + h[startIdx];
    queue.push_back(startIdx);
    inQueue[startIdx] = true;

    while (!queue.empty()) {
        int bestIdx = 0;

        for (int i = 0; i < queue.size(); i++) {
            int currentNode = queue[i];
            int bestNode = queue[bestIdx];
            if (f[currentNode] < f[bestNode]) bestIdx = i;
            else if (f[currentNode] == f[bestNode] && h[currentNode] < h[bestNode]) bestIdx = i;
        }
        int current = queue[bestIdx];
        queue.erase(queue.begin() + bestIdx);
        inQueue[current] = false;

        if (current == exitIdx) return buildEvacuationPath(parent, g, h, f, startIdx, exitIdx, n);
        processed[current] = true;

        for (int i = 0; i < totalNodes; i++) {
            if (weightMatrix[current][i] == 0) continue;
            if (processed[i]) continue;
            double newCost = g[current] + weightMatrix[current][i];
            if (newCost < g[i]) {
                g[i] = newCost;
                f[i] = g[i] + h[i];
                parent[i] = current;

                if (inQueue[i] == false) {
                    queue.push_back(i);
                    inQueue[i] = true;
                }
            }
        }
    }

    return NULL;
}