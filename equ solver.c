



#include <stdio.h>
#include <windows.h>
#include <string.h>


typedef struct equ {
    char varname;
    char equation[50];
} equ;


float solve(equ equ);

char *format(equ equ);

char *insertAt(char *str, char c1, int index);

char **toParts(char *equ, char valName);

char *addThings(char *equ, char valName);

int contains(const char *str, char c1);

int findChar(char *str, char c1, int a, int b);

int findLast(char *str, char c1, int index);

int* partsToInts(char** parts, char valName);




int main(int argc, char **argv) {
    equ eq1;
    eq1.varname = 'z';
    strcpy(eq1.equation, "3z = 9z - 15");
    float solution = solve(eq1);
    printf("%f\n",solution);
    return 0;
}


char *format(equ equ) {
    char *after = malloc(strlen(equ.equation) + 1);
    int after_counter = 0;
    int i = 0;
    //removing spaces
    while (equ.equation[i] != '\0') {
        if (equ.equation[i] != ' ') {
            after[after_counter] = equ.equation[i];
            after_counter++;
        }
        i++;
    }
    //adding the null byte
    after[after_counter] = '\0';
    return after;
}


char *insertAt(char *str, char c1, int index) {
    //adding one char worth of memory to the tempStr string
    char *tempStr = malloc(strlen(str) + 2);
    //coping up to the index where we want to insert
    strncpy(tempStr, str, index);
    //inserting the char
    tempStr[index] = c1;
    //coping from the index of the original string to the end to the original string to the new string
    strncpy(tempStr + index + 1, str + index, strlen(str) + 1 - index);
    return tempStr;
}


char *addThings(char *equ, char valName) {

    //if the first char is not - or +, we need to add +
    if (equ[0] != '-' && equ[0] != '+') {
        equ = insertAt(equ, (char) '+', 0);
        //free(temp);
    }

    //running through the string
    for (int i = 0; i < strlen(equ); i++) {
        //is the current char the char of the valName?
        if (equ[i] == valName) {
            //inserting if the first char is the valName or the char before equ[i] is not a number
            if (i == 0 || !isdigit(equ[i - 1])) {
                equ = insertAt(equ, '1', i);
            }
        }
    }
    return equ;
}

char **toParts(char *equ, char valName) {
    //from no spaces to no spaces and with all of the things
    equ = addThings(equ, valName);
    char **parts = malloc(strlen(equ));

    //copy equ so we can use it again
    char *temp = malloc(strlen(equ));
    strcpy(temp, equ);
    //looping through the parts
    char *curPart = strtok(temp, "+-");
    //index of the sign of curPart
    int curSign = 0;
    int i = 0;
    //tmptmp should be deleted, it's just to see that the thingy is working.
    char* tmptmp;
    //separating the string by every time we have - or +
    while (curPart) {
        //add to the list only if the parts are not inside a ().
        if(!contains(curPart,'(')&&!contains(curPart,')')){
            tmptmp = insertAt(curPart, equ[curSign], 0);
            *(parts + i) = tmptmp;
            i++;
        }
        //getting the sign of the part
        if (curPart != NULL)
            curSign += (int) strlen(curPart) + 1;
        curPart = strtok(NULL, "+-");
    }
    free(temp);
    //adding null byte
    *(parts + i) = 0;//<- the same as -> *(parts + i) = '\0';
    return parts;
}


int contains(const char *str, char c1) {
    for(int i = 0; i < (int)sizeof(str)/sizeof(char);i++){
        if(str[i] == c1)
            return 1;
    }

    return 0;
}

float solve(equ equ) {
    //removing spaces
    char *formatStr = format(equ);
    //separating to left and right side on the = sign
    char *left = strdup(strtok(formatStr, "="));
    char *right = strdup(strtok(NULL, "="));

    //separating to left and right parts
    char** leftParts = toParts(left,equ.varname);
    char** rightParts = toParts(right,equ.varname);
    //parsing the parts to sums as int arrays
    int* leftSum = partsToInts(leftParts,equ.varname);
    int* rightSum = partsToInts(rightParts,equ.varname);

    //creating the sum of both sumXs from both sides
    float sumX = (float) (leftSum[0] - rightSum[0]);
    //creating the sum of both side's numSums
    float sumNum = (float) (rightSum[1] - leftSum[1]);
    free(leftSum);
    free(rightSum);
    //the equation is numSum/xSum so we are handling devision by 0
    if (sumX == 0){
        return 999999;
    }
    //return the value of the variable
    return (sumNum / sumX);
}

int findChar(char *str, char c1, int a, int b) {
    if (b == 0){
        b = (int)strlen(str);
    }
    else if (b > strlen(str) || a > b)
        return -1;
    for (int i = a; i < b; i++) {
        if (str[i] == c1)
            return i;
    }
    return -1;
}


int findLast(char *str, char c1, int index) {
    int val = findChar(str, c1, index, 0);
    if (val == -1 || val < index)
        return -1;
    int next = findLast(str, c1, index + 1);
    if (next > val)
        return next;
    return val;
}


int* partsToInts(char **parts, char valName) {
    //summing the variables and the numbers of the equ
    int xSum = 0;
    int numSum = 0;
    int i = 0;
    char* curPart;
    for (i = 0; *(parts + i); i++) {
        //is it a variable?
        if (contains(*(parts + i), valName)) {
            curPart = insertAt(*(parts + i), '\0', (int) strlen(*(parts + i)) - 1);
            xSum += (int) strtol(curPart, NULL, 10);
            free(curPart);
        }
            //if its not a variable, its a number
        else
            numSum += (int) strtol(*(parts + i), NULL, 10);
    }
    int* ret = calloc(2,sizeof(int));
    ret[0] = xSum;
    ret[1]= numSum;
    return ret;
}



























