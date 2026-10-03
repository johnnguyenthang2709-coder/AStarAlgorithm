#include "Algo.h"

void freePath(PathNode *head)
{
    while (head != nullptr)
    {
        PathNode *temp = head;
        head = head->next;
        delete temp;
    }
}

void addUndirectedEdge(double matrix[100][100], int u, int v, double cost = 1)
{
    matrix[u][v] = cost;
    matrix[v][u] = cost;
}

void printAndFree(PathNode *path)
{
    printPath(path);
    freePath(path);
}

void printNonZeroWeights(double matrix[100][100], int totalNodes)
{
    cout << "Generated weight matrix entries:\n";
    for (int i = 0; i < totalNodes; i++)
    {
        for (int j = 0; j < totalNodes; j++)
        {
            if (matrix[i][j] != 0)
            {
                cout << "weightMatrix[" << i << "][" << j << "] = "
                     << matrix[i][j] << "\n";
            }
        }
    }
}

int main()
{
    //------------------------------------------
    // TASK 1
    //------------------------------------------
    cout << "========== TASK 1 ==========\n";

    double social[100][100] = {0};

    addUndirectedEdge(social, 0, 1);
    addUndirectedEdge(social, 0, 2);
    addUndirectedEdge(social, 1, 3);
    addUndirectedEdge(social, 1, 4);
    addUndirectedEdge(social, 2, 4);
    addUndirectedEdge(social, 3, 5);
    addUndirectedEdge(social, 4, 5);

    printAndFree(findSocialPath(social, 0, 5));

    //------------------------------------------
    // TASK 2
    //------------------------------------------
    cout << "\n========== TASK 2 ==========\n";

    double droneWeights[100][100] = {0};
    int coords[100][2] = {0};

    coords[0][0] = 0;
    coords[0][1] = 0;
    coords[1][0] = 2;
    coords[1][1] = 1;
    coords[2][0] = 1;
    coords[2][1] = 4;
    coords[3][0] = 4;
    coords[3][1] = 2;
    coords[4][0] = 5;
    coords[4][1] = 5;

    droneWeights[0][1] = 2.5;
    droneWeights[0][2] = 4.0;
    droneWeights[1][3] = 2.5;
    droneWeights[1][2] = 2.0;
    droneWeights[2][4] = 2.5;
    droneWeights[3][4] = 3.0;

    cout << "Mode 1 - Manhattan:\n";
    printAndFree(findDronePath(droneWeights, coords, 0, 4, 1));

    cout << "\nMode 2 - Euclidean:\n";
    printAndFree(findDronePath(droneWeights, coords, 0, 4, 2));

    cout << "\nMode 3 - Chebyshev:\n";
    printAndFree(findDronePath(droneWeights, coords, 0, 4, 3));

    //------------------------------------------
    // TASK 3
    //------------------------------------------
    cout << "\n========== TASK 3 ==========\n";

    int warehouse[100][100] = {0};
    int warehouseExample[5][5] = {
        {0, 0, 1, 0, 0},
        {0, 0, 1, 0, 0},
        {1, 0, 0, 1, 0},
        {0, 1, 0, 1, 0},
        {0, 0, 1, 0, 0}};

    for (int i = 0; i < 5; i++)
    {
        for (int j = 0; j < 5; j++)
        {
            warehouse[i][j] = warehouseExample[i][j];
        }
    }

    printAndFree(findWarehousePath(warehouse, 5, 5, 0, 0, 4, 4, 2));

    //------------------------------------------
    // TASK 4
    //------------------------------------------
    cout << "\n========== TASK 4 ==========\n";

    int floorPlan[100][100] = {0};
    int floorExample[4][4] = {
        {0, 0, 1, 0},
        {0, 0, 1, 0},
        {1, 0, 0, 0},
        {0, 0, 1, 0}};
    double evacuationWeights[100][100] = {0};

    for (int i = 0; i < 4; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            floorPlan[i][j] = floorExample[i][j];
        }
    }

    printAndFree(findEvacuationPath(floorPlan, 4, 4, 0, 0, 3, 3, evacuationWeights, 2));
    printNonZeroWeights(evacuationWeights, 4 * 4);

    return 0;
}
