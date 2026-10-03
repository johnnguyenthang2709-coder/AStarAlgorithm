#include "PathNode.h"
#include <iostream>

using namespace std;

void printPath(PathNode *head)
{
    cout << "Solution Path:\n";
    while (head != nullptr)
    {
        cout << "Node: " << head->name
             << " | f: " << head->f
             << " | g: " << head->g
             << " | h: " << head->h << "\n";
        head = head->next;
    }
}
