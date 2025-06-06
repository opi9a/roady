import argparse
import sys

from .Roady import Roady
from .get_gc import update_tour_gcs, print_stage_gc

def main():

    parser = argparse.ArgumentParser(
        epilog=('make the passed tour, eg "france 23"')
    )

    parser.add_argument('country', type=str, help='the country')
    parser.add_argument('year', type=int, help='the year eg "23"')
    parser.add_argument('-c', '--update-gc',
                        action='store_true', default=False,
                        help="update gc standings pdfs for stages")
    parser.add_argument('stage', type=int, nargs='?',
                        help='the stage to update gc')

    args = parser.parse_args()

    if args.update_gc:
        yr = int(args.year) + 2000
        if args.stage is None:
            print(f'looking to update gc for {args.country} {yr}')
            update_tour_gcs(args.country, yr)
        else:
            print(f'updating gc for {args.country} {yr} stage {args.stage}')
            print_stage_gc(args.stage, args.country, yr)
            
    else:
        rd = Roady(args.country, args.year)
        rd.make_roadbook_pdf()

if __name__ == '__main__':
    sys.exit(main())



