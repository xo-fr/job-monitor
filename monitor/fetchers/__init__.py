from . import custom, generic, instahyre

FETCHERS = {
    "greenhouse": generic.greenhouse,
    "lever": generic.lever,
    "ashby": generic.ashby,
    "workday": generic.workday,
    "eightfold": generic.eightfold,
    "smartrecruiters": generic.smartrecruiters,
    "amazon": custom.amazon,
    "microsoft": custom.microsoft,
    "instahyre": instahyre.instahyre,
}
