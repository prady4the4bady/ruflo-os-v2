export interface DetailedPlan {
  thoughtProcess: string;
  subTasks: {
    name: string;
    description: string;
    requiredTools: string[];
    dependencies: string[];
  }[];
}
